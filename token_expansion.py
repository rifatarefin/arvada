import random
from typing import List

from grammar import Grammar, Rule
from oracle import ExternalOracle, ParseException
from parse_tree import ParseNode

import string

from replacement_utils import get_strings_with_replacement, nt_in_tree, fixup_terminal

digit_type = 0
uppercase_type = 1
lowercase_type = 2
letter_type = 3
whitespace_type = 4

MAX_SAMPLES = 10

def rules_to_add(rule_start):
    if rule_start == "tdigit":
        r = Rule(rule_start)
        for i in range(10):
            r.add_body([f'"{i}"'])
        return [r]
    if rule_start == "tdigits":
        r = Rule(rule_start)
        r.add_body(['tdigit'])
        r.add_body(["tdigit", "tdigits" ])
        return [r, rules_to_add("tdigit")[0]]
    if rule_start == "tinteger":
        r = Rule(rule_start)
        r.add_body(['tdigit'])
        r.add_body(["tnzdigit", "tdigits" ])
        nz = Rule("tnzdigit")
        for i in range(1, 10):
            nz.add_body([f'"{i}"'])
        return [r, nz] + rules_to_add("tdigits")
    return []


def try_strings(oracle: ExternalOracle, candidates: List[str]):

    for candidate in candidates:
        try:
            oracle.parse(candidate)
        except ParseException:
            return False
    return True


def generalize_digits_in_rule(oracle: ExternalOracle, grammar: Grammar, trees: List[ParseNode], rule_start: str, body_idxs: List[int]):

    existing_bodies = [fixup_terminal(body[0]) for idx, body in enumerate(grammar.rules[rule_start].bodies) if idx in body_idxs]

    if all(len(body) == 1 for body in existing_bodies):
        single_digit_candidates = [s for s in string.digits if s not in existing_bodies]
    else:
        single_digit_candidates = []

    integer_candidates = []
    digits_candidates = []
    for i in range(MAX_SAMPLES):
        first_dig = random.choice("123456789")
        leng = random.randint(1, 10)
        other_digs  = random.sample(string.digits, leng)
        integer_candidates.append(first_dig + ''.join(other_digs))
        digits_candidates.append('0' + ''.join(other_digs))

    digit_ok = True
    ints_ok = True
    digits_ok = True

    for tree in [tree for tree in trees if nt_in_tree(tree, rule_start)]:
        if digit_ok and single_digit_candidates:
            candidates = get_strings_with_replacement(tree, rule_start, single_digit_candidates)
            if not try_strings(oracle, candidates):
                digit_ok = False
                ints_ok = False
                digits_ok = False
        if ints_ok:
            candidates = get_strings_with_replacement(tree, rule_start, integer_candidates)
            if not try_strings(oracle, candidates):
                ints_ok = False
                digits_ok = False
        if digits_ok:
            candidates = get_strings_with_replacement(tree, rule_start, digits_candidates)
            if not try_strings(oracle, candidates):
                digits_ok = False

    replace_str = ''
    if digits_ok:
        replace_str = 'tdigits'
    elif ints_ok:
        replace_str = 'tinteger'
    elif digit_ok:
        replace_str = 'tdigit'
    if replace_str == "":
        return [], ""
    else:
        return body_idxs, replace_str



def expand_tokens(oracle : ExternalOracle, grammar : Grammar, trees: List[ParseNode]):
    """
    The idea is to expand the terminal tokens of the grammar as permmited by "oracle"
    """
    rule_starts = set(grammar.rules.keys())
    def is_terminal(elem):
        return elem not in rule_starts

    original_rules = list(grammar.rules.items())
    for rule_start, rule in original_rules:
        idxs_to_replace = set()
        bodies_to_add = set()
        bodies = rule.bodies
        terminal_body_idxs = [idx for idx, body in enumerate(bodies) if len(body) == 1 and is_terminal(body[0])]
        if len(terminal_body_idxs) == 0:
            # Nothing to expand here, folks
            continue
        idxs_by_type = classify_terminals_by_type(bodies, terminal_body_idxs)

        # Digit expansion...
        if idxs_by_type[digit_type]:
            digit_bodies_to_replace, replace_str = generalize_digits_in_rule(oracle, grammar, trees, rule_start, idxs_by_type[digit_type])
            idxs_to_replace.update(digit_bodies_to_replace)
            bodies_to_add.add(replace_str)

        for body_idx in sorted(idxs_to_replace, reverse = True):
            rule.bodies.pop(body_idx)
        for nt_name in bodies_to_add:
            rule.add_body([nt_name])
            rs_to_add = rules_to_add(nt_name)
            for r_to_add in rs_to_add:
                if r_to_add.start not in grammar.rules:
                    grammar.add_rule(r_to_add)

    return grammar


def classify_terminals_by_type(bodies, terminal_body_idxs):
    """
    Find the upper (generalizable) character class for all the terminal bodies in bodies
    """
    idxs_by_type = {digit_type: [], uppercase_type: [], lowercase_type: [], letter_type: [], whitespace_type: []}
    for idx in terminal_body_idxs:
        body = bodies[idx][0]
        body = fixup_terminal(body)
        if all(c in string.digits for c in body):
            idxs_by_type[digit_type].append(idx)
        elif all(c in string.whitespace for c in body):
            idxs_by_type[whitespace_type].append(idx)
        elif all(c in string.ascii_letters for c in body):
            if all(c in string.ascii_uppercase for c in body):
                idxs_by_type[uppercase_type].append(idx)
            elif all(c in string.ascii_lowercase for c in body):
                idxs_by_type[lowercase_type].append(idx)
            else:
                idxs_by_type[letter_type].append(idx)
    return idxs_by_type