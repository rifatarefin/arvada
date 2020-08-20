from typing import Tuple, List

from parse_tree import ParseNode

def fixup_terminal(payload):
    if len(payload) >= 3 and payload.startswith('"') and payload.endswith('"'):
        payload = payload[1:-1]
    return payload


def get_all_replacement_strings(tree: ParseNode, nt_to_replace: str):
    """
    Get all the possible strings derived from `tree` where all possible combinations
    (including the combination of len 0) of instances of `nt_to_replace` are replaced
    by '[[:REPLACEME]]'.
    >>> left_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])]), ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> right_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> left_l2 = [ParseNode('t2', False, left_l3)]
    >>> right_l2 = [ParseNode('t2', False, right_l3)]
    >>> big_tree = ParseNode('t0', False, \
                     [ParseNode('t0', False, left_l2), \
                      ParseNode('t4', False, [ParseNode('"*"', True, [])]), \
                      ParseNode('t0', False, right_l2)] \
                     )
    >>> no_occ_tree = ParseNode('t4', False, [ParseNode('"*"', True, [])])
    >>> get_all_replacement_strings(no_occ_tree, 't2')
    ['*']
    >>> one_occ_tree = right_l2[0]
    >>> sorted(get_all_replacement_strings(one_occ_tree,  't2'))
    ['4', '[[:REPLACEME]]']
    >>> three_occ_tree = left_l2[0]
    >>> sorted(get_all_replacement_strings(three_occ_tree, 't2'))
    ['44', '4[[:REPLACEME]]', '[[:REPLACEME]]', '[[:REPLACEME]]4', '[[:REPLACEME]][[:REPLACEME]]']
    >>> sorted(get_all_replacement_strings(big_tree,  't2'))
    ['44*4', '44*[[:REPLACEME]]', '4[[:REPLACEME]]*4', '4[[:REPLACEME]]*[[:REPLACEME]]', '[[:REPLACEME]]*4', '[[:REPLACEME]]*[[:REPLACEME]]', '[[:REPLACEME]]4*4', '[[:REPLACEME]]4*[[:REPLACEME]]', '[[:REPLACEME]][[:REPLACEME]]*4', '[[:REPLACEME]][[:REPLACEME]]*[[:REPLACEME]]']
    """
    replacement_strings = []
    if tree.is_terminal:
        return [fixup_terminal(tree.payload)]

    if tree.payload == nt_to_replace:
        replacement_strings.append('[[:REPLACEME]]')

    strings_per_child = [get_all_replacement_strings(c, nt_to_replace) for c in tree.children]
    string_prefixes = ['']
    for strings_for_child in strings_per_child:
        string_prefixes =[prefix + string_for_child for prefix in string_prefixes for string_for_child in strings_for_child]
    replacement_strings.extend(string_prefixes)

    return list(set(replacement_strings))

def get_all_rule_replacement_strs(tree: ParseNode, replacee_rule: Tuple[str, List[str]], replacee_posn: int):
    """
    Get all the possible strings derived from `tree` where all possible combinations
    (including the combination of len 0) of instances of `nt_to_replace` are replaced
    by '[[:REPLACEME]]'.
    >>> left_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])]), ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> right_l3 = [ParseNode('t2', False, [ParseNode('"4"', True, [])])]
    >>> left_l2 = [ParseNode('t2', False, left_l3)]
    >>> right_l2 = [ParseNode('t2', False, right_l3)]
    >>> big_tree = ParseNode('t0', False, \
                     [ParseNode('t0', False, left_l2), \
                      ParseNode('t4', False, [ParseNode('"*"', True, [])]), \
                      ParseNode('t0', False, right_l2)] \
                     )
    >>> no_occ_tree = ParseNode('t4', False, [ParseNode('"*"', True, [])])
    >>> replacee_rule = ('t0', ['t2'])
    >>> replacee_posn = 0
    >>> get_all_rule_replacement_strs(no_occ_tree, replacee_rule, replacee_posn)
    ['*']
    >>> one_child_one_occ = ParseNode('t0', False, right_l2)
    >>> sorted(get_all_rule_replacement_strs(one_child_one_occ, replacee_rule, replacee_posn))
    ['4', '[[:REPLACEME]]']
    >>> two_children_one_occ = ParseNode('t0', False, left_l2)
    >>> sorted(get_all_rule_replacement_strs(two_children_one_occ, replacee_rule, replacee_posn))
    ['44', '[[:REPLACEME]]']
    >>> sorted(get_all_rule_replacement_strs(big_tree,replacee_rule, replacee_posn))
    ['44*4', '44*[[:REPLACEME]]', '[[:REPLACEME]]*4', '[[:REPLACEME]]*[[:REPLACEME]]']
    """
    start = replacee_rule[0]
    body = [fixup_terminal(elem) for elem in replacee_rule[1]]
    if tree.is_terminal:
        return [fixup_terminal(tree.payload)]
    strings_per_child = [get_all_rule_replacement_strs(c, replacee_rule, replacee_posn) for c in tree.children]
    if tree.payload == start:
        tree_body = [fixup_terminal(c.payload) for c in tree.children]
        if tree_body == body:
            strings_per_child[replacee_posn].append('[[:REPLACEME]]')

    string_prefixes = ['']
    for strings_for_child in strings_per_child:
        string_prefixes =[prefix + string_for_child for prefix in string_prefixes for string_for_child in strings_for_child]

    return list(set(string_prefixes))

if __name__ == "__main__":
    import doctest
    doctest.testmod()