import re
from parse_tree import ParseNode
from generator import *
from graph import Graph

# Globally unique nonterminal number
next_tid = 1 # Reserve t0 for the start nonterminal

def allocate_tid():
    """
    Returns a new, unqiue nonterminal name.
    """
    global next_tid
    nt_name = 't%d' % (next_tid)
    next_tid += 1
    return nt_name

def build_start_grammars(config, leaves):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    LEAVES is a list of positive examples, each expressed as a list of tokens
    (ParseNode objects).

    Returns a set of starting grammar generators whose corresponding grammars
    each match at least one input example.
    """
    trees, nt_grouping = build_trees(leaves)
    gens = [build_generator(config, tree) for tree in trees]
    grammar_nodes = [gen.grammar_node for gen in gens]
    merge_trees(config, grammar_nodes, nt_grouping)
    gens = [GrammarGenerator(config, g_n) for g_n in grammar_nodes]
    return gens

def group(trees):
    """
    TREES is composed of half-built ParseTrees. Each of the intermediate
    ParseTrees are represented as a list of nodes at the top-most layer.

    Given a list of TREES, computes and returns a map of the most common
    payloads in the ParseNodes. Each returned map entry is given a unique
    identifier ti for some i > 1, reserving i = 0 for the start node.

    Trivial groups are filtered out, including groups that only appear once or
    groups that only consist of one token.

    Returns the group first sorted by frequency so that most frequently occuring
    substrings come first, then sorted by length, so that longer substrings are
    preferred, like in the maximal-munch rule.
    """
    counts = {}
    for tree_lst in trees:
        for i in range(len(tree_lst)):
            for j in range(i + 1, len(tree_lst) + 1):
                tree_sublist = tree_lst[i:j]
                tree_substr = ''.join([t.payload for t in tree_sublist])
                tree_substr = re.sub('t\d+', 't', tree_substr)
                if tree_substr in counts:
                    count, sublist, id = counts[tree_substr]
                    counts[tree_substr] = (count + 1, sublist, id)
                else:
                    counts[tree_substr] = (1, tree_sublist, allocate_tid())

    # Filter out tokens that only appear once
    counts = {k:v for k, v in counts.items() if v[0] > 1}
    # Filter out nonterminals composed of only one token
    counts = {k:v for k, v in counts.items() if len(v[1]) > 1}

    # Sort first by frequency, then by key-length
    counts = sorted(counts.items(), key=lambda elem: len(elem[0]), reverse=True)
    return sorted(counts, key=lambda elem: elem[1][0], reverse=True)

def matches(grouping, layer):
    """
    LAYER is the top layer of one half-built ParseTree.

    The GROUPING of the TREES is an implicit map of a list of tokens to the
    frequency at which the list occurs in the top layer of TREES, with most
    frequent token appearing first.

    Returns the index at which grouping appears in layer, and returns -1 if
    the grouping does not appear in the layer.
    """
    ng, nl = len(grouping), len(layer)
    for i in range(nl):
        layer_ind = i # Index into layer
        group_ind = 0 # Index into group
        while group_ind < ng and layer_ind < nl and layer[layer_ind].payload == grouping[group_ind].payload:
            layer_ind += 1
            group_ind += 1
        if group_ind == ng: return i
    return -1

def apply(grouping, trees):
    """
    TREES is composed of half-built ParseTrees. Each of the intermediate
    ParseTrees are represented as a list of nodes at the top-most layer. This
    algorithm applies GROUPING to the topmost layer of each tree to progress
    in building the tree. This algorithm should be repeatedly called until
    each of the trees consists of a list of a single node, the root.

    The GROUPING of the TREES is an implicit map of a list of tokens to the
    frequency at which the list occurs in the top layer of TREES, with most
    frequent token appearing first.

    Algorithm: For each of the trees in TREES, greedily group the ParseNodes in
    accord with GROUPING so that the most frequently appearing tokens are grouped
    first. Perform only one iteration of this greedy grouping scheme, so that
    in order to completely build the tree, this method must be called many times.
    Grouped nodes become the children of new ParseNodes, which are inserted
    into the top layer list of the trees. The updated top layer lists are returned.

    In other words, this method, given the ith layer of the tree and the set of
    groupings for that layer, returns the i + 1st layer of the tree, for each
    of the input trees in TREES.
    """

    def apply_single(group_lst, tree_lst):
        """
        Applies the grouping to a single tree in the manner defined above.
        Only a single new ParseNode is created at one time.
        Returns the updated TREE_LST.

        If no groupings can be found, create a start node pointing to each
        of the remaining nodes in the parse tree.
        """
        if len(tree_lst) == 0:
            return tree_lst

        for group_str, tup in grouping:
            count, group_lst, id = tup
            ng = len(group_lst)
            ind = matches(group_lst, tree_lst)
            if ind != -1:
                parent = ParseNode(group_str, False, tree_lst[ind : ind + ng])
                parent.payload = id
                tree_lst[ind : ind + ng] = [parent]
                return tree_lst
        start = ParseNode('t0', False, tree_lst[:])
        start.payload = 't0'
        return [start]

    return [apply_single(grouping, tree) for tree in trees]

def build_trees(leaves):
    """
    LEAVES should be a list of lists (one list for each input example), where
    each sublist contains the tokens that built that example, as ParseNodes.

    Iteratively builds parse trees from each of the examples and returns a list
    of ParseNode references

    Algorithm:
        1. Initialization
            - S <- input examples
            - G <- group(S)
        2. while there is some unfinished tree:
            a. Build new ParseNodes from S
            b. S <- set of ParseNodes
        3. return the set of finished ParseNodes

    This method also computes groups for nonterminals, which are used for merging
    the finished trees in later algorithms
    """
    def finished(layers):
        """
        Helper function that returns when each of the trees in layers is
        composed of just a single root (has a length of 1), indicating that
        the algorithm is finished building all the trees.
        """
        return all([len(layer) <= 1 for layer in layers])

    grouping = group(leaves)
    nt_grouping = {}
    layers = leaves

    while not finished(layers):
        layers = apply(grouping, layers)
        for grp_key, grp_val in group(layers):
            if 't' not in grp_key:
                continue
            if grp_key not in nt_grouping:
                nt_grouping[grp_key] = grp_val
            else:
                cnt, nodes, id = nt_grouping[grp_key]
                nt_grouping[grp_key] = (cnt + 1, nodes, id)

    # Sort nt_grouping before returning it, and give merged nonterminals a different
    # identifier than normal nonterminals
    nt_grouping = sorted(nt_grouping.items(), key=lambda elem: len(elem[0]), reverse=True)
    nt_grouping = sorted(nt_grouping, key=lambda elem: elem[1][0], reverse=True)
    for i in range(len(nt_grouping)):
        grp_str, tup = nt_grouping[i]
        cnt, nodes, grp_id = tup
        grp_id = grp_id.replace('t', 'v')
        nt_grouping[i] = (grp_str, (cnt, nodes, grp_id))

    return [layer[0] for layer in layers], nt_grouping

def merge_trees(config, grammar_nodes, nt_grouping):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    GRAMMAR_NODES is a list of fully constructed grammars.

    The NT_GROUPING (of the parse trees that constructed the grammars) is an
    implicit map of a list of tokens (at least one of which is a nonterminal)
    to the frequency at which the list occured throughout the building of the
    parse trees, with most frequent ones appearing first.

    This method merges the GRAMMAR_NODES by the groupings in NT_GROUPING. The
    build_tree algorithm may run into a situtation where it defines two separate
    rules t1 -> ( t2 ) and t3 -> ( t4 ) where t2 -> int + int, t4 -> int * int.
    The rules t1 and t3 should be the same parenthisization rule. This method
    fixes this issue by defining t1 -> ( ty ), t3 -> ( ty ) where ty -> t2 | t4.

    This method is MUTATIVE on the set of grammars, and so has not return value.
    """
    def merge_single(grammar_node, grammar_rule, grp_str, grp_id, alternation_set):
        """
        Performs the above merge operation on a single GRAMMAR_RULE on a given
        GRAMMAR_NODE for a single type of nonterminal grouping GRP_STR. Updates
        the grammar to include the new alternation rules.

        GRP_ID is a pre-allocated unique ID for the new nonterminal created
        for this group.

        ALTERNATION_SET is a set of nonterminals [t2, t4] in the above example.
        """
        # If the group matches the rule, add the corresponding nonterminals
        # in the rule into the group's alternation set
        rule_body = ''.join([child.choice for child in grammar_rule.children])

        if grp_str in re.sub('t\d+', 't', rule_body):
            pattern = re.sub('t', 't\d+', grp_str)
            nt_matches = re.findall(pattern, rule_body)

            # Define a set of new rules for this grammar
            new_rules = [RuleNode(config, grp_id, [SymbolNode(config, nt, False)]) for nt in nt_matches]
            grammar_node.children.extend(new_rules)

            # Add the nonterminal matches to the alternation set
            if grp_id not in alternation_set:
                alternation_set[grp_id] = (grp_str, nt_matches, new_rules)
            else:
                _, alt_set, rules = alternation_set[grp_id]
                alternation_set[grp_id] = (grp_str, alt_set + nt_matches, rules + new_rules)

            # Update the nonterminals to point to the grp_id
            for child in grammar_rule.children:
                if child.choice in nt_matches:
                    child.choice = grp_id

    # Populate the alternation set by iterating through all the rules
    # Also, update the grammar to contain new alternation rules.
    alternation_set = {}
    for grp_str, tup in nt_grouping:
        _, _, grp_id = tup
        for grammar_node in grammar_nodes:
            for rule in grammar_node.children:
                merge_single(grammar_node, rule, grp_str, grp_id, alternation_set)

    # Maps a given nonterminal to the list of grammars in which it appears
    nt_to_grammar = {}
    for grammar_node in grammar_nodes:
        for rule_node in grammar_node.children:
            if rule_node.lhs in nt_to_grammar:
                nt_to_grammar[rule_node.lhs].append(grammar_node)
            else:
                nt_to_grammar[rule_node.lhs] = [grammar_node]

    # Add the altneration rules to each grammar. Note that if an alternation
    # rule's altnernation nonterminal points to a nonterminal that does not
    # currently exist in the grammar, it will still be added. The nonterminal
    # that does not exist will be added in later stages.
    for grp_id in alternation_set:
        _, _, new_rules = alternation_set[grp_id]
        for grammar_node in nt_to_grammar[grp_id]:
            grp_rules = [rule_node for rule_node in grammar_node.children if rule_node.lhs == grp_id]
            already_added_nts = set([next(iter(rule_node.children)).choice for rule_node in grp_rules])
            for new_rule in new_rules:
                if next(iter(new_rule.children)).choice not in already_added_nts:
                    grammar_node.children.append(new_rule)

    # Populate nts_to_add, which maps an alternation nonterminal to the set of
    # nonterminals reachable from it in any of the starting grammars. This will
    # be used in order to merge grammars together and fill in rules that any
    # particular grammar does not have
    nts_to_add = {}
    for group_tid in alternation_set:
        _, _, rule_nodes = alternation_set[group_tid]
        nts_to_add[group_tid] = set()
        for rule_node in rule_nodes:
            # alt_nt := one of the altnernation nonterminals, e.g. t2 or t4 in
            # the above example
            alt_nt = next(iter(rule_node.children)).choice
            nts_to_add[group_tid].add(alt_nt)

            # Isolate one of the grammars that the alt_nt appears in. Since the rule
            # for alt_nt is always the same across all grammars, any grammar that
            # the nt appears in will do
            grammar_node = next(iter(nt_to_grammar[alt_nt]))

            # Create a directed graph out of the nonterminals in this grammar
            vertices = set([rule_node.lhs for rule_node in grammar_node.children])
            grammar_graph = Graph(vertices)
            for rule_node in grammar_node.children:
                for symbol_node in rule_node.children:
                    if not symbol_node.is_terminal:
                        grammar_graph.add_edge(rule_node.lhs, symbol_node.choice)

            # Explore the graph starting at alt_nt to figure out all nonterminals
            # reachable from alt_nt. Add these to the set of nts_to_add for
            # this particular alternation rule.
            for nt in grammar_graph.reachable_from(alt_nt):
                nts_to_add[group_tid].add(nt)

    # Loop through each of the grammars, and for any grammars that contain an
    # alternation defined above, add all the rules corresponding to any ~missing~
    # alternation nonterminals to this grammar. Note that we only need to add
    # missing nonterminals, because those that are already there correspond exactly
    # to any we will find in our traversal.
    for grammar_node in grammar_nodes:
        defined_nts = set([rule_node.lhs for rule_node in grammar_node.children])
        rules_to_add = set()
        for rule_node in grammar_node.children:
            if rule_node.lhs in alternation_set:
                for nt in nts_to_add[rule_node.lhs]:
                    # nt takes on a nonterminal in this grammar that is not yet
                    # defined. We must find the rule in another grammar and
                    # include that rule here.
                    if nt not in defined_nts:
                        # A grammar node for some grammar that has the rule
                        rule_grammar = next(iter(nt_to_grammar[nt]))

                        # The corresponding RuleNode in the grammar
                        new_rule = next(iter([rule_node for rule_node in rule_grammar.children if rule_node.lhs == nt]))

                        # Add this to the set of rules_to_add, which will be
                        # added to the grammar after we cease iterating
                        rules_to_add.add(new_rule)

        # Finished finding all the rules to add to this grammar, now add them
        grammar_node.children.extend(rules_to_add)

def build_generator(config, tree):
    """
    CONFIG is the required configuration options for GrammarGenerator classes.

    TREE is a fully constructed parse tree. This method builds a GrammarGenerator
    based on the parse tree, and returns it.
    """
    def build_rules(grammar_node, parse_node):
        """
        Adds the rules defined in PARSE_NODE and all of its subtrees to the
        GRAMMAR_NODE via recursion.
        """
        # Terminals and nodes with no children do not define rules
        if parse_node.is_terminal or len(parse_node.children) == 0:
            return

        # The current ParseNode defines a rule. Add this rule to the grammar.
        #        t0
        #       / | \
        #     t1  a  b
        #    / |
        #    ...
        # E.g. the ParseNode t0 defines the rule t0 -> t1 a b
        rule_body = [SymbolNode(config, child.payload, child.is_terminal) for child in parse_node.children]
        grammar_node.children.append(RuleNode(config, parse_node.payload, rule_body))

        # Recurse on the children of this ParseNode so the rule they define
        # are also added to the grammar.
        # Terminals and nodes without children are taken care of by the base case.
        for child in parse_node.children:
            build_rules(grammar_node, child)

    # Initial grammar node without children, then fill its children.
    # Return the corresponding GrammarGenerator
    grammar_node = GrammarNode(config, tree.payload, [])
    build_rules(grammar_node, tree)
    return GrammarGenerator(config, grammar_node)

# Example:
# leaves = [[ParseNode('abc', True, None), ParseNode('d', True, None), ParseNode('e', True, None), ParseNode('f', True, None), ParseNode('g', True, None)], [ParseNode('abc', True, None), ParseNode('d', True, None), ParseNode('e', True, None)]]
# config = {'TERMINALS': ['"a"', '"b"', '', '"c"', '"d"', '"e"', '"f"', '"g"'], 'NONTERMINALS': ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9', 't10', 't11', 't12', 't13', 't14'], 'NUM_RULES': 15, 'MAX_RHS_LEN': 3, 'POS_EXAMPLES': 100, 'NEG_EXAMPLES': 100, 'MAX_NEG_EXAMPLE_SIZE': 100, 'MAX_TREE_DEPTH': 10}
# arithmetic = [[ParseNode('(', True, None), ParseNode('int', True, None), ParseNode('+', True, None), ParseNode('int', True, None), ParseNode(')', True, None)], [ParseNode('(', True, None), ParseNode('int', True, None), ParseNode('*', True, None), ParseNode('int', True, None), ParseNode(')', True, None)], [ParseNode('int', True, None), ParseNode('+', True, None), ParseNode('int', True, None)], [ParseNode('int', True, None), ParseNode('*', True, None), ParseNode('int', True, None)]]
# config = {'TERMINALS': ['"int"', '"+"', '"*"', '"("', '")"', ''], 'NONTERMINALS': ['t0', 't1', 't2'], 'NUM_RULES': 7, 'MAX_RHS_LEN': 5, 'POS_EXAMPLES': 100, 'NEG_EXAMPLES': 100, 'MAX_NEG_EXAMPLE_SIZE': 100, 'MAX_TREE_DEPTH': 10}
#
# starts = build_start_grammars(config, arithmetic)
# for gen in starts:
#     print('%s\n\n' % (gen.generate_grammar()))
