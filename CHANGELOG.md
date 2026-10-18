## [2.0.0](https://github.com/EmperorCookie/nocli/compare/v1.0.1...v2.0.0) (2026-10-18)

### ⚠ BREAKING CHANGES

* **constructors:** `ConstructorAbc`, the new base of every constructor in place of `Constructor`, now owns `count` and `repeatable`: a constructor declares the CLI values consumed and whether the option repeats, and claims annotations through `can_handle` and `resolve`
* **config:** `CliConfig(count=...)` and `CliConfig(repeatable=...)` now apply to plain callables only, since a `ConstructorAbc` owns `count` and `repeatable`; conflicting values raise `ConfigConflictError`
* **constructors:** `BoolConstructor` now takes `finalizer` and `invalidFinalizer` in place of `invalid`: `finalizer` converts the determined `bool` into the final value, and `invalidFinalizer` converts unrecognized input instead of raising
* **exceptions:** Invalid CLI definitions now raise `CliBuildError` subclasses, such as `ParamConstructorError` for an unhandled annotation or `UnsupportedParameterError` for `*args`, instead of `TypeError` or `ValueError`
* **config:** `ParamSpec` is now `CliParamSpec`
* **exceptions:** Every exception now lives in `nocli.exceptions`, out of `nocli` and `nocli.constructors`: `nocli.ParserError` is now `nocli.exceptions.ParserError`

### Added

* **config:** `CliConfig(displayDefault=...)` to set the default value shown in help ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **constructors:** `FlagConstructor`, `UnionConstructor`, `NoneConstructor` and `CallableConstructor`, and `ConstructorAbc.from_annotation` to derive a constructor from a type hint when composing constructors by hand ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **exceptions:** `cause` and `reason` on `ConstructionError`, exposing the exception the constructor raised ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **maintainers:** An in-repo semantic-release runner where `patch-note:` lines in a commit message become release notes; ruff and pyright are now dev dependencies ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **type-hints:** `Cli(constructors=...)` and `nocli.DEFAULT_CONSTRUCTORS`: annotations are now resolved by an ordered list of constructors, each deciding which annotations to handle ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **type-hints:** Detection of tuples, collections and mappings from annotations: `list[int]` is repeatable, `tuple[int, str]` takes two values and `dict[str, int]` takes pairs ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **type-hints:** Unions of any members, tried in declaration order (`int | Literal["auto"]`); `X | None` leaves the option absent and `None | X` reads an empty value as `None` ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))

### Modified

* **config:** `CliConfig(count=...)` and `CliConfig(repeatable=...)` now apply to plain callables only, since a `ConstructorAbc` owns `count` and `repeatable`; conflicting values raise `ConfigConflictError` ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **constructors:** `BoolConstructor` now takes `finalizer` and `invalidFinalizer` in place of `invalid`: `finalizer` converts the determined `bool` into the final value, and `invalidFinalizer` converts unrecognized input instead of raising ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **constructors:** `ConstructorAbc`, the new base of every constructor in place of `Constructor`, now owns `count` and `repeatable`: a constructor declares the CLI values consumed and whether the option repeats, and claims annotations through `can_handle` and `resolve` ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **exceptions:** Invalid CLI definitions now raise `CliBuildError` subclasses, such as `ParamConstructorError` for an unhandled annotation or `UnsupportedParameterError` for `*args`, instead of `TypeError` or `ValueError` ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))
* **help:** The help now takes the type of each value from the constructor (`list[str]`, `int | 'auto'`), so `Literal` and enum choices appear in the type instead of a separate `Choices:` line ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))

### Fixed

* **help:** The help now shows defaults produced by `defaultFactory` ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))

### Updated

* **constructors:** `OptionalConstructor` now builds on `UnionConstructor` and `NoneConstructor`, and `ChoicesConstructor` claims `Literal` and enum annotations ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))

### Renamed

* **config:** `ParamSpec` is now `CliParamSpec` ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))

### Moved

* **exceptions:** Every exception now lives in `nocli.exceptions`, out of `nocli` and `nocli.constructors`: `nocli.ParserError` is now `nocli.exceptions.ParserError` ([df32a9c](https://github.com/EmperorCookie/nocli/commit/df32a9c79c4672e3ffad724de2e9a975f8011b81))

## [1.0.1](https://github.com/EmperorCookie/nocli/compare/v1.0.0...v1.0.1) (2026-09-28)


### Bug Fixes

* Build wheel from source tree instead of sdist ([f560e26](https://github.com/EmperorCookie/nocli/commit/f560e2693fb82e53257097c23b5643df8d4dd9bd))
* Typo in readme ([e0fba84](https://github.com/EmperorCookie/nocli/commit/e0fba84193b3fdf14630cbc21b4ddebfe213dde3))

## 1.0.0 (2026-09-28)


### Features

* First public release ([341bc3c](https://github.com/EmperorCookie/nocli/commit/341bc3c177ec18fb13d20cf506428ddb8878a072))
