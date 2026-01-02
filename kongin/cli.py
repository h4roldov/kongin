"""
Command-line interface for Kongin.
"""

import argparse
import json
import sys

from . import OAIClient, DSpaceExporter, __version__


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='kongin',
        description='OAI-PMH harvester with DSpace export'
    )
    parser.add_argument(
        '--version', '-V',
        action='version',
        version=f'kongin {__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # harvest command
    harvest_parser = subparsers.add_parser('harvest', help='Harvest records from OAI-PMH')
    harvest_parser.add_argument('url', help='OAI-PMH endpoint URL')
    harvest_parser.add_argument(
        '--prefix', '-p',
        default='oai_dc',
        help='Metadata prefix (default: oai_dc)'
    )
    harvest_parser.add_argument(
        '--set', '-s',
        dest='set_spec',
        help='Set to harvest'
    )
    harvest_parser.add_argument(
        '--from', '-f',
        dest='from_date',
        help='From date (YYYY-MM-DD)'
    )
    harvest_parser.add_argument(
        '--until', '-u',
        dest='until_date',
        help='Until date (YYYY-MM-DD)'
    )
    harvest_parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Maximum records to harvest'
    )
    harvest_parser.add_argument(
        '--output', '-o',
        help='Output JSON file'
    )
    harvest_parser.add_argument(
        '--format',
        choices=['json', 'dspace', 'csv'],
        default='dspace',
        help='Output format (default: dspace)'
    )

    # identify command
    identify_parser = subparsers.add_parser('identify', help='Get repository info')
    identify_parser.add_argument('url', help='OAI-PMH endpoint URL')

    # sets command
    sets_parser = subparsers.add_parser('sets', help='List available sets')
    sets_parser.add_argument('url', help='OAI-PMH endpoint URL')

    # formats command
    formats_parser = subparsers.add_parser('formats', help='List metadata formats')
    formats_parser.add_argument('url', help='OAI-PMH endpoint URL')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == 'harvest':
            cmd_harvest(args)
        elif args.command == 'identify':
            cmd_identify(args)
        elif args.command == 'sets':
            cmd_sets(args)
        elif args.command == 'formats':
            cmd_formats(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_harvest(args):
    """Execute harvest command."""
    client = OAIClient(args.url)
    records = []

    print(f"Harvesting from {args.url}...", file=sys.stderr)

    for i, record in enumerate(client.list_records(
        metadata_prefix=args.prefix,
        set_spec=args.set_spec,
        from_date=args.from_date,
        until_date=args.until_date
    )):
        records.append(record)
        if args.limit and i + 1 >= args.limit:
            break
        if (i + 1) % 100 == 0:
            print(f"  {i + 1} records...", file=sys.stderr)

    print(f"Harvested {len(records)} records", file=sys.stderr)

    # Generate output
    if args.format == 'dspace':
        exporter = DSpaceExporter()
        output = exporter.to_json(records)
    elif args.format == 'json':
        output = json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False)
    elif args.format == 'csv':
        lines = ['title,creators,date,identifier']
        for r in records:
            title = (r.title or '').replace('"', '""')
            creators = '; '.join(r.creators).replace('"', '""')
            date = r.date or ''
            identifier = r.identifier
            lines.append(f'"{title}","{creators}","{date}","{identifier}"')
        output = '\n'.join(lines)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(output)


def cmd_identify(args):
    """Execute identify command."""
    client = OAIClient(args.url)
    info = client.identify()

    print(f"Repository: {info.get('repository_name', 'N/A')}")
    print(f"Base URL: {info.get('base_url', 'N/A')}")
    print(f"Protocol: {info.get('protocol_version', 'N/A')}")
    print(f"Earliest: {info.get('earliest_datestamp', 'N/A')}")
    print(f"Granularity: {info.get('granularity', 'N/A')}")
    if info.get('admin_emails'):
        print(f"Admin: {', '.join(info['admin_emails'])}")


def cmd_sets(args):
    """Execute sets command."""
    client = OAIClient(args.url)
    sets = client.list_sets()

    for s in sets:
        print(f"{s['set_spec']}: {s['set_name']}")


def cmd_formats(args):
    """Execute formats command."""
    client = OAIClient(args.url)
    formats = client.list_metadata_formats()

    for f in formats:
        print(f"{f['prefix']}: {f.get('namespace', 'N/A')}")


if __name__ == '__main__':
    main()
