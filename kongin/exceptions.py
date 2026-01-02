"""
Custom exceptions for the OAI-PMH client.

Includes OAI-PMH protocol-specific error codes as defined in the specification:
https://www.openarchives.org/OAI/openarchivesprotocol.html#ErrorConditions
"""


class OAIClientError(Exception):
    """Base class for exceptions raised by the OAI client."""


class OAIRequestError(OAIClientError):
    """Exception raised for errors in the HTTP request to the OAI service."""


class OAIResponseError(OAIClientError):
    """Exception raised for errors in the response from the OAI service."""


# ==================== OAI-PMH Protocol Errors ====================

class OAIProtocolError(OAIClientError):
    """
    Base class for OAI-PMH protocol errors.

    These errors are returned in the XML response body, not as HTTP status codes.
    """

    def __init__(self, code: str, message: str = ''):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}" if message else code)


class BadArgumentError(OAIProtocolError):
    """
    The request includes illegal arguments, is missing required arguments,
    includes a repeated argument, or values for arguments have an illegal syntax.
    """

    def __init__(self, message: str = ''):
        super().__init__('badArgument', message)


class BadVerbError(OAIProtocolError):
    """
    Value of the verb argument is not a legal OAI-PMH verb,
    the verb argument is missing, or the verb argument is repeated.
    """

    def __init__(self, message: str = ''):
        super().__init__('badVerb', message)


class BadResumptionTokenError(OAIProtocolError):
    """
    The value of the resumptionToken argument is invalid or expired.
    """

    def __init__(self, message: str = ''):
        super().__init__('badResumptionToken', message)


class CannotDisseminateFormatError(OAIProtocolError):
    """
    The metadata format identified by the value given for the metadataPrefix
    argument is not supported by the item or by the repository.
    """

    def __init__(self, message: str = ''):
        super().__init__('cannotDisseminateFormat', message)


class IdDoesNotExistError(OAIProtocolError):
    """
    The value of the identifier argument is unknown or illegal in this repository.
    """

    def __init__(self, message: str = ''):
        super().__init__('idDoesNotExist', message)


class NoRecordsMatchError(OAIProtocolError):
    """
    The combination of the values of the from, until, set and metadataPrefix
    arguments results in an empty list.
    """

    def __init__(self, message: str = ''):
        super().__init__('noRecordsMatch', message)


class NoMetadataFormatsError(OAIProtocolError):
    """
    There are no metadata formats available for the specified item.
    """

    def __init__(self, message: str = ''):
        super().__init__('noMetadataFormats', message)


class NoSetHierarchyError(OAIProtocolError):
    """
    The repository does not support sets.
    """

    def __init__(self, message: str = ''):
        super().__init__('noSetHierarchy', message)


# Mapping from OAI-PMH error codes to exception classes
OAI_ERROR_MAP = {
    'badArgument': BadArgumentError,
    'badVerb': BadVerbError,
    'badResumptionToken': BadResumptionTokenError,
    'cannotDisseminateFormat': CannotDisseminateFormatError,
    'idDoesNotExist': IdDoesNotExistError,
    'noRecordsMatch': NoRecordsMatchError,
    'noMetadataFormats': NoMetadataFormatsError,
    'noSetHierarchy': NoSetHierarchyError,
}
