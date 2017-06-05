import argparse
import re
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
from operator import itemgetter


def read_tsv(fp):
    headers = []
    for i, line in enumerate(fp):
        line = line.strip().split('\t')
        if i == 0:
            headers = line
            continue
        yield dict(zip(headers, line))


def parse_decimal(value):
    return Decimal(re.sub(r'[^0-9.,-]+', '', value).replace(',', '.'))


def fraction_as_decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def process(data):
    by_tag = defaultdict(list)
    for line in data:
        qty = int(line['qty'])
        if 'total' in line:
            line_price = parse_decimal(line['total'])
        elif 'unit' in line:
            line_price = parse_decimal(line['unit']) * qty
        else:
            raise NotImplementedError('no total or unit in line %r' % line)
        name = line['name']
        tags = Counter(line['tags'])
        total_tags = sum(tags.values())
        for tag, count in tags.items():
            share = Fraction(count, total_tags)
            by_tag[tag].append({
                'line': line,
                'name': name,
                'share': share,
                'total_qty': qty,
                'split_qty': (share * qty),
                'total_price': line_price,
                'split_price': Decimal(float(share)) * line_price,
            })
    return by_tag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    args = ap.parse_args()
    with open(args.input) as infp:
        data = list(read_tsv(infp))
    by_tag = process(data)
    for tag, tag_items in sorted(by_tag.items()):
        total_price = sum(item['split_price'] for item in tag_items)
        total_qty = sum(item['split_qty'] for item in tag_items)
        header_line = '%s: %s items, total split price %.2f' % (tag, fraction_as_decimal(total_qty), total_price)
        print()
        print(header_line)
        print('=' * len(header_line))
        name_len = max(len(item['name']) for item in tag_items)
        for item in sorted(tag_items, key=itemgetter('name')):
            print('%-*s %4s .. %6s' % (
                name_len, item['name'],
                item['split_qty'],
                item['split_price'],
            ))


if __name__ == '__main__':
    main()
