"""Very basic template system used by the test framework.

Templates may specify {% num %}...{% end %} expressions that are
filtered against the current pass number. See the ``feedplatform.test``
docs for more information.

Example:

    import template
    template.render(template, pass_num)
"""

import re
import operator


__all__ = ('render',)


tag_re = re.compile('{%(.*?)%}')

def render(content, current_pass):
    output = ""
    is_tag = True
    open_tags = 0
    skipping = False

    for bit in tag_re.split(content):
        is_tag = not is_tag
        token = bit.strip()

        if is_tag and token == 'end':
            open_tags -= 1
            if open_tags < 0:
                raise Exception('end tag mismatch')
            if open_tags < skipping:
                skipping = False

        elif is_tag:
            open_tags += 1
            if not skipping:
                if not evaluate_tag(token, current_pass):
                   # skip until tag-level falls below current state
                   # again, e.g. account for nested tags to find
                   # the right "end", from where we'll pick it up.
                   skipping = open_tags

        elif skipping:
            continue

        else:
            output += bit

    if open_tags != 0:
        raise SyntaxError('not all tags closed')

    return output


def evaluate_tag(expr, current_pass):
    """Tests ``expr`` against current pass, returns a bool.

    Example input: 1, >1, =3, <2
    """

    # normalize: '\t> 5 ' => '>5'
    expr = expr.strip().replace(' ', '')

    p, v = expr[:2], expr[2:]             # two two char ops
    if not p in ('>=', '<=',):
        p, v = expr[:1], expr[1:]         # try one char ops
        if not (p in '<>='):
            # assume now op specified, >= is the default
            p = '>='
            v = expr

    # if the op is valid, the rest must be a number
    if not v.isdigit():
        raise ValueError("'%s' not a valid tag expression " % expr)

    value = int(v)
    ops = {'=': (operator.eq,),
           '>': (operator.gt,),
           '<': (operator.lt,),
           '>=': (operator.gt, operator.eq),
           '<=': (operator.lt, operator.eq)}[p]
    return any([op(current_pass, value) for op in ops])