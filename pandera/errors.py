"""pandera-specific errors."""

import warnings
from enum import Enum
from typing import Any, Dict, List, NamedTuple


class BackendNotFoundError(Exception):
    """
    Raised when a backend is not found for a particular schema of check backend.
    """


class ReducedPickleExceptionBase(Exception):
    """Base class for Exception with non-conserved state under pickling.

    Derived classes define attributes to be transformed to
    string via `TO_STRING_KEYS`.
    """

    TO_STRING_KEYS: List[str] = []

    def __reduce__(self):
        """Exception.__reduce__ is incompatible. Override with custom layout.

        Each attribute in `TO_STRING_KEYS` is replaced by its string
        representation.
        """
        state = {
            key: str(val)
            if key in self.TO_STRING_KEYS and val is not None
            else val
            for key, val in self.__dict__.items()
        }
        state["args"] = self.args  # message may not be in __dict__
        return (
            self.__class__.__new__,  # object creation function
            (self.__class__,),  # arguments to said function
            state,  # arguments to `__setstate__` after creation
        )

    @classmethod
    def _unpickle_warning(cls):
        """Create the warning message about state loss in pickling."""
        return (
            f"Pickling {cls.__name__} does not preserve state: "
            f"Attributes {cls.TO_STRING_KEYS} become string "
            "representations."
        )

    def __setstate__(self, state):
        """Show warning during unpickling."""
        warnings.warn(self._unpickle_warning())
        return super().__setstate__(state)


class ParserError(ReducedPickleExceptionBase):
    """Raised when data cannot be parsed from the raw into its clean form."""

    TO_STRING_KEYS = ["failure_cases"]

    def __init__(self, message, failure_cases):
        super().__init__(message)
        self.failure_cases = failure_cases


class SchemaInitError(Exception):
    """Raised when schema initialization fails."""


class SchemaDefinitionError(Exception):
    """Raised when schema definition is invalid on object validation."""


class SchemaError(ReducedPickleExceptionBase):
    """Raised when object does not pass schema validation constraints."""

    TO_STRING_KEYS = [
        "schema",
        "data",
        "failure_cases",
        "check",
        "check_output",
        "reason_code",
    ]

    def __init__(
        self,
        schema,
        data,
        message,
        failure_cases=None,
        check=None,
        check_index=None,
        check_output=None,
        reason_code=None,
    ):
        super().__init__(message)
        self.schema = schema
        self.data = data
        self.failure_cases = failure_cases
        self.check = check
        self.check_index = check_index
        self.check_output = check_output
        self.reason_code = reason_code


class BaseStrategyOnlyError(Exception):
    """Custom error for reporting strategies that must be base strategies."""


SCHEMA_ERRORS_SUFFIX = """

Usage Tip
---------

Directly inspect all errors by catching the exception:

```
try:
    schema.validate(dataframe, lazy=True)
except SchemaErrors as err:
    err.failure_cases  # dataframe of schema errors
    err.data  # invalid dataframe
```
"""


class FailureCaseMetadata(NamedTuple):
    """Consolidated failure cases, summary message, and error counts."""

    failure_cases: Any
    message: str
    error_counts: Dict[str, int]


class SchemaErrorReason(Enum):
    """Reason codes for schema errors."""

    INVALID_TYPE = "invalid_type"
    DATATYPE_COERCION = "dtype_coercion_error"
    COLUMN_NOT_IN_SCHEMA = "column_not_in_schema"
    COLUMN_NOT_ORDERED = "column_not_ordered"
    DUPLICATE_COLUMN_LABELS = "duplicate_dataframe_column_labels"
    COLUMN_NOT_IN_DATAFRAME = "column_not_in_dataframe"
    SCHEMA_COMPONENT_CHECK = "schema_component_check"
    DATAFRAME_CHECK = "dataframe_check"
    CHECK_ERROR = "check_error"
    DUPLICATES = "duplicates"
    WRONG_FIELD_NAME = "wrong_field_name"
    SERIES_CONTAINS_NULLS = "series_contains_nulls"
    SERIES_CONTAINS_DUPLICATES = "series_contains_duplicates"
    SERIES_CHECK = "series_check"
    WRONG_DATATYPE = "wrong_dtype"
    INDEX_CHECK = "index_check"
    ADD_MISSING_COLUMN_NO_DEFAULT = "add_missing_column_no_default"


class SchemaErrors(ReducedPickleExceptionBase):
    """Raised when multiple schema are lazily collected into one error."""

    TO_STRING_KEYS = [
        "schema",
        "failure_cases",
        "data",
    ]

    def __init__(
        self,
        schema,
        schema_errors: List[SchemaError],
        data: Any,
    ):
        self.schema = schema
        self.schema_errors = schema_errors
        self.data = data

        failure_cases_metadata = schema.get_backend(
            data
        ).failure_cases_metadata(schema.name, schema_errors)
        self.error_counts = failure_cases_metadata.error_counts
        self.failure_cases = failure_cases_metadata.failure_cases
        super().__init__(failure_cases_metadata.message)
