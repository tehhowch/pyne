#!/usr/bin/env python

"""The classes in this module aid the specification of tally `units`  in
:py:class:`pyne.simplesim.cards.ICellSurfTally` (see examples below). The class
focuses on the ability to specify cells and surfaces that are nested within
universes or other cells in nearly arbitrarily complex ways. Apart from making
user input clearler, this class has methods that help with creating cell
comments and mcnp strings. 

The names of classes here are fairly short, so the user may not want to import
the entire namespace. A suggested way to import the module is::

    import pyne.simplesim.nestedgeom as ng


Usage Examples
--------------
The subclasses of :py:class:`ICellSurfTally` can take as input any subclass of
:py:class:`IUnit`. The following shows different ways in which complex units
can be built.


The following string in MCNP (<LAT-SPEC> is discussed below)::

(scA, scB) < (cC, cD[<LAT-SPEC>]) < U=u1 < (cE, cF, cG)

is obtained with the following input::

([scA, scB], [cC, (cD, ([li0,li1],[lj0,lj1],[lk0,lk1]))], 'u1', [cE, cF, cG])

The optional <LAT-SPEC> specifies which lattice elements to consider
from a lattice cell. It has 3 possible forms, and the MCNP syntax is
compared to the syntax used here::

MCNP
li0:li1 lj0:lj1 lk0:lk1
[li0,li1],[lj0,lj1],[lk0,lk1]

li0 lj0 lk0, li1 lj1 lk1, ...
[[li0, lj0, lk0], [li1, lj1, lk1], ...]

The following is a non-exhaustive table of eligible units of input::

generic                                             simplesim
scA                                                 'scA'
union of scA, scB, scC                              ['scA', 'scB', 'scC'] 
univA                                               'univA'
union of univA                                      ['univA']
scA in scB                                          ('scA', 'scB')
scA in scB in scC                                   ('scA', 'scB', 'scC')
scA in univA                                        ('scA', 'univA')
scA in union of univA                               ('scA', ['univA'])
scA in union of scB and scC             ('scA', ['scB', 'scC'])
scA in univA in scB                           ('scA', 'univA', 'scB')
scA in scB, lattice elements <LAT-SPEC> ('scA', ('scB', <LAT-SPEC>))
(scA and scB) in scC in (scD and scE)  ((scA, scB), 

union('scA', 'scB', 'scC')   union(sc('A'), sc('B'), sc('C'))
univ('univA') 
union(univ('univA'))
'scA' in 'scB'             surf('A').in(surf('B'))
'scA' in 'scB' in 'scC'        surf('A').in(surf('B').in('scC'))
'scA' in univ('univA')       sc('A').in(univ('A'))
'scA' in union(univ('A'))    sc('A').in(union(univ('A')))
'scA' in union('scB', 'scC') sc('A').in(union('scB', 'scC'))
'scA' in univ('univA') in 'scC'  sc('A').in(univ('A').in(sc('C')))
'scA' in lat('scB', []) in ...   sc('A').in(sc('B').lat([]))

vec('scA', 'scB').in(sc('C').in(vec('scD', 'scE')))


The last of these is called `multiple bin format` in MCNP, and creates
a total of 4 tally `units`, one for 'scA' through'scD'.


"""

import numpy as np

from pyne.simplesim import cards, definition

class IUnit(object):
    """Abstract base class for tally units. The user does not use this class
    directly.
    
    """
    def __init__(self, up=None, down=None):
        """Currently, the two keyword arguments are not actually used, but are
        sometimes set directly, after initialization.

        """
        self.up = up
        self.down = down

    def __lt__(self, next_level_up):
        """The user can use the < operator to perform the operation of
        :py:meth:`of`, e.g. (cells/surfs) < (cells/univ)
        
        """
        return self.of(next_level_up)

    def of(self, next_level_up):
        """Returns a unit where ``self`` must be in ``next_level_up`` to be
        tallied. ``self`` must be a cell or surface, or `vector` or `union`
        thereof (cell/surf), and
        ``next_level_up`` can be a cell or universe, or union thereof
        (cells/univ).

        """
        self.up = next_level_up
        self.up.down = self
        if self.down: return self.down
        else:         return self

    def __or__(self, right):
        """A convenient way to call :py:meth:`union`."""
        return self.union(right)

    def union(self, right):
        """Returns a :py:class:`union` of ``self`` with ``right``."""
        if isinstance(self, union):
            self.brothers += [right]
            return self
        else:
            return union(self, right)

    def __and__(self, right):
        """A convenient way to call :py:meth:`vector`."""
        return self.vector(right)

    def vector(self, right):
        """Returns a :py:class:`vec` of ``self`` with ``right."""
        if isinstance(self, vec):
            self.sisters += [right]
            return self
        else:
            return vec(self, right)

    def comment(self, inner):
        return "{0}{1}{2}{3}".format(
                " (" if self.up and not self.down else "",
                inner,
                (" in" + self.up.comment()) if self.up else "",
                ")" if self.down and not self.up else "")

    def mcnp(self, float_format, sim, inner):
        return "{0}{1}{2}{3}".format(
                " (" if self.up and not self.down else "",
                inner,
                (" <" + self.up.mcnp(float_format, sim)) if self.up else "",
                ")" if self.down and not self.up else "")


class ICellSurf(IUnit):
    """Abstract base class for surfaces and cells in the lowest level of the
    nested geometry. The user directly uses the subclasses of this class. For
    cells in higher levels of nesting (e.g. closer to the real world), see
    :py:class:`ucell`.

    """
    def __init__(self, name):
        """
        Parameters
        ----------
        name : str
            Name of the surface or cell. Depending on the subclass, the name is
            looked up appropriately in the system definition to obtain the
            surface or cell number.

        """
        super(ICellSurf, self).__init__()
        self.name = name


class surf(ICellSurf):
    """The user uses this class directly to reference a surface in the system
    definition for tallying.

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.surf

    """
    def comment(self):
        return super(surf, self).comment(" surf {0!r}".format(self.name))

    def mcnp(self, float_format, sim):
        return super(surf, self).mcnp(float_format, sim,
                " {0}".format(sim.sys.surface_num(self.name)))


class cell(ICellSurf):
    """The user uses this class directly to reference a cell in the system
    definition for tallying.

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.cell

    """
    def comment(self, inner=None):
        return super(cell, self).comment(" cell {0!r}{1}".format(self.name,
                inner if inner else ""))

    def mcnp(self, float_format, sim, inner=None):
        return super(cell, self).mcnp(float_format, sim,
                " {0}{1}".format(sim.sys.cell_num(self.name),
                    inner if inner else ""))


class ucell(cell):
    """This is subclassed from :py:class:`cell`. It is to be used for
    higher-level cells (closer to the real world), and has an additional
    attribute to specify specific lattice elements from this cell if it is a
    lattice cell.

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.ucell

    """
    def __init__(self, name, lat_spec=None):
        """
        Parameters
        ----------
        name : str
            See :py:class:`ICellSurf`.
        lat_sec : subclass of :py:class:`LatticeSpec`

        """
        super(ucell, self).__init__(name)
        self.lat_spec = lat_spec

    def comment(self):
        return super(ucell, self).comment(
                self.lat_spec.comment() if self.lat_spec else "")

    def mcnp(self, float_format, sim):
        return super(ucell, self).mcnp(float_format, sim,
                self.lat_spec.mcnp(float_format, sim) if self.lat_spec else "")


class univ(IUnit):
    """A universe. It is used in higher levels of nesting (closer to the real
    world). The class, given the name of a universe in the system, looks up the
    appropriate universe number.

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.univ

    """
    def __init__(self, name):
        """
        Parameters
        ----------
        name : str
            Name of the universe in the system definition.  

        """
        super(univ, self).__init__()
        self.name = name

    def comment(self):
        return super(univ, self).comment(" univ {0!r}".format(self.name))

    def mcnp(self, float_format, sim):
        return super(univ, self).mcnp(float_format, sim,
                " U={0}".format(sim.sys.universe_num(self.name)))


class union(IUnit):
    """A union of surfaces, cells, or of a single universe.

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.union

    """
    def __init__(self, *args):
        """
        Paramemters
        -----------
        *args : list of instances of :py:class:`IUnit` subclasses.

        """
        # all args must be a instance of Unit or its subclasses.
        self.brothers = args
        super(union, self).__init__()

    def comment(self):
        string = ""
        counter = 0
        for bro in self.brothers:
            counter += 1
            string += bro.comment()
            if counter < len(self.brothers): string += ","
        return super(union, self).comment(" union of ({0})".format(string))

    def mcnp(self, float_format, sim):
        string = ""
        for bro in self.brothers:
            string += bro.mcnp(float_format, sim)
        return super(union, self).mcnp(float_format, sim, 
                " ({0})".format(string))


class vec(IUnit):
    """A "vector" of surfaces or cells. This class named after the vectorized
    notation that can be used in MATLAB, as this class allows the specification
    of multiple units of input in a single unit. Typically, a :py:class:`vec`
    is the first or last element in a nested unit. The following are two
    example usages of this class, and their equivalent in comment as two
    separate units::

        # surf('A') < ucell('C')     surf('B') < ucell('C')
        vec(surf('A'), surf('B')) < ucell('C')
        # surf('A') < ucell('C')     surf('A') < ucell('D')
        surf('A') < vec(ucell('C'), ucell('D'))
    """
    # Named after matlab's vectorized notation
    def __init__(self, *args):
        # all args must be a instance of Unit or its subclasses.
        self.sisters = args
        super(vec, self).__init__()

    def comment(self):
        string = ""
        counter = 0
        for sis in self.sisters:
            counter += 1
            string += sis.comment()
            if counter < len(self.sisters): string += ","
        return super(vec, self).comment(" over ({0})".format(string))

    def mcnp(self, float_format, sim):
        string = ""
        for sis in self.sisters:
            string += sis.mcnp(float_format, sim)
        return super(vec, self).mcnp(float_format, sim, string)


class ILatticeSpec(object):
    """Abstract base class for lattice element specifiers. The user does not
    use this class directly. There are 3 subclasses:

    - :py:class:`lin` : a single linear index of a lattice element.
    - :py:class:`rng` : x, y, and z index range of lattice elements.
    - :py:class:`cor` : list coordinates of lattice elments.
    
    """
    def comment(self, inner):
        return "-lat {0}".format(inner)

    def mcnp(self, float_format, sim, inner):
        # Lattice specification goes in square brackets.
        return "[{0}]".format(inner)


class lin(ILatticeSpec):
    """A single linear index of a lattice element.

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.lin

    """
    def __init__(self, linear_index):
        """
        Parameters
        ----------
        linear_index : int
            Linear (1-D) of a lattice element for the lattice cell that this
            specifier becomes a part of.

        """
        self.index = linear_index

    def comment(self):
        return super(lin, self).comment("linear idx {0:d}".format(self.index))

    def mcnp(self, float_format, sim):
        return super(lin, self).mcnp(float_format, sim,
                "{0:d}".format(self.index))


class rng(ILatticeSpec):
    """A range of lattice elements.

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.rng

    """
    def __init__(self, x_bounds=[0, 0], y_bounds=[0, 0], z_bounds=[0, 0]):
        """
        Parameters
        ----------
        x_bounds : 2-element list of int, optional
            Something like [0,5] for lattice elements i=0 through i=5. First
            element is less than the second element. Don't
            specify to leave as [0, 0].
        y_bounds : 2-element list of int, optional
            First element is less than the second element. Don't specify to
            leave as [0, 0].
        z_bounds : 2-element list of int, optional
            First element is less than the second element. Don't specify to
            leave as [0, 0].

        Examples
        --------
        In the following, there is no y dimension::

            myrange = rng([0, 5], z_bounds=[0, 2])

        """
        super(rng, self).__init__()
        self.x_bounds = x_bounds
        self.y_bounds = y_bounds
        self.z_bounds = z_bounds

    def comment(self):
        return super(rng, self).comment(
                "x range {0[0]:d}:{0[1]:d}, y range {1[0]:d}:{1[1]:d}, "
                "z range {2[0]:d}:{2[1]:d}".format(
                self.x_bounds, self.y_bounds, self.z_bounds))

    def mcnp(self, float_format, sim):
        return super(rng, self).mcnp(float_format, sim,
                "{0[0]:d}:{0[1]:d} {1[0]:d}:{1[1]:d} {2[0]:d}:{2[1]:d}".format(
                self.x_bounds, self.y_bounds, self.z_bounds))


class cor(LatticeSpec):
    """A list of lattice element coordinates (in indices).

    .. inheritance-diagram:: pyne.simplesim.nestedgeom.cor

    """
    def __init__(self, points=[0, 0, 0]):
        """
        Parameters
        ----------
        points : 3-element list of int, list of lists, optional
            Coordinates of a lattice element, or a list of coordinates.

        Examples
        --------
        The following work::

            latspec = cor()
            latspec = cor([1, 2, 3])
            latspec = cor([ [1, 2, 3], [-1, 3, -2]])

        """
        super(cor, self).__init__()
        # We want a nested list, even if the user doesn't provide it. If the
        # first element of the list is an int, then it's not a 3-element list
        # or numpy array, so we need to nest it in a loop for the methods to
        # work.
        if type(points[0]) is int: points = [points]
        self.points = points

    def comment(self):
        string = "coords"
        counter = 0
        for pt in self.points:
            counter += 1
            string += " ({0[0]:d}, {0[1]:d}, {0[2]:d})".format(pt)
            if counter < len(self.points): string += ","
        return super(cor, self).comment(string)

    def mcnp(self, float_format, sim):
        string = ""
        counter = 0
        for pt in self.points:
            counter += 1
            string += " {0[0]:d} {0[1]:d} {0[2]:d}".format(pt)
            if counter < len(self.points): string += ","
        return super(cor, self).mcnp(float_format, sim, string)










