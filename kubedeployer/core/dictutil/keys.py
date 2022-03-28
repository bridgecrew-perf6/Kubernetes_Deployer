def check_keys(element, *keys):
    '''
    Check if *keys (nested) exists in `element` (dict).
    '''
    if not isinstance(element, dict):
        raise AttributeError('check_keys() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError('check_keys() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except (KeyError, TypeError):
            return False
    return True

def read_key(element, *keys):
    '''
    Read keys (str or list) from element (dict) and return the value.
    '''
    if not isinstance(element, dict):
        raise AttributeError('read_key() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError('read_key() expects at least two arguments, one given.')

    _element = element
    if len(keys) == 1:
        key = ''.join(keys)
        return  _element[key]
    else:
        for key in keys:
            _element = _element[key]
        return _element