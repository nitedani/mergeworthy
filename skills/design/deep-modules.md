# Deep modules

- A **module** is anything with an interface and an implementation: a function, a class, a package.
- Its **interface** is everything a caller must know to use it: types, invariants, ordering, errors, configuration.
- A module is **deep** when a lot of behavior sits behind a small interface, and **shallow** when the interface is nearly as complex as what it hides.
- A **seam** is where behavior can change without editing that place; it is where an interface lives.
- Apply the deletion test: imagine deleting the module. If complexity vanishes, it was a pass-through; if it reappears across its callers, it earns its place.
- Test through the interface. Needing to test past it means the module has the wrong shape.
- Add a seam only when two implementations vary across it; one is hypothetical.
- Accept dependencies rather than create them, and return results rather than produce side effects.
- Replace, don't layer: once tests exist at the deeper interface, delete the tests on the shallow parts it absorbed.
