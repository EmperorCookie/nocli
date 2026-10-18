from ._base import CliBuildError, NocliError, ParserError
from ._cli import (
    ConfigConflictError,
    InvalidNameError,
    NoFlagsError,
    ParamConstructorError,
    ParamNameError,
    UnsupportedParameterError,
)
from ._constructors import (
    ConstructorShapeError,
    IterableElementShapeError,
    NoConstructorError,
    TupleElementShapeError,
    UnionConstructionError,
    UnionMemberShapeError,
    UnsupportedAnnotationError,
)
from ._parser import (
    ConstructionError,
    DuplicateFlagError,
    FlagAlreadyPassedError,
    MissingOptionError,
    MissingValueError,
    UnexpectedTokenError,
    UnrecognizedTokenError,
)
from ._subcommand import DuplicateCommandError
