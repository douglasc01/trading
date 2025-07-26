import re


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase string to snake_case.

    Arguments:
        camel_str (str): String in camelCase format

    Returns:
        str: String in snake_case format
    Examples:
        >>> camel_to_snake("requestThis")
        'request_this'
        >>> camel_to_snake("getUserData")
        'get_user_data'
        >>> camel_to_snake("XMLParser")
        'xml_parser'
    """

    # insert underscore before uppercase letters that follow lowercase letters or digits
    s1 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", camel_str)

    # insert underscore between consecutive uppercase letters followed by lowercase
    s2 = re.sub("([A-Z])([A-Z][a-z])", r"\1_\2", s1)

    return s2.lower()
