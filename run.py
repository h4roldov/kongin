#!/usr/bin/env python3
"""
Example script demonstrating Kongin OAI-PMH harvesting.

Usage:
    python run.py <oai_url> [--prefix PREFIX] [--set SET] [--output FILE]

Example:
    python run.py https://repositorio.example.org/oai --prefix oai_dc
"""

import argparse
import json
import os
import sys

from kongin import OAIClient


def main():
    parser = argparse.ArgumentParser(
        description='Harvest records from an OAI-PMH repository'
    )
    parser.add_argument(
        'url',
        nargs='?',
        default=os.environ.get('OAI_URL'),
        help='OAI-PMH endpoint URL (or set OAI_URL env var)'
    )
    parser.add_argument(
        '--prefix', '-p',
        default='oai_dc',
        help='Metadata prefix (default: oai_dc)'
    )
    parser.add_argument(
        '--set', '-s',
        dest='set_spec',
        help='Set specification to harvest'
    )
    parser.add_argument(
        '--output', '-o',
        default='output.json',
        help='Output JSON file (default: output.json)'
    )
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Disable SSL certificate verification'
    )

    args = parser.parse_args()

    if not args.url:
        print("Error: URL required. Provide as argument or set OAI_URL env var.")
        sys.exit(1)

    # Initialize client
    requests_args = {}
    if args.no_verify:
        requests_args['verify'] = False

    client = OAIClient(url=args.url, requests_args=requests_args)

    # Build harvest params
    params = {
        'verb': 'ListRecords',
        'metadataPrefix': args.prefix,
    }
    if args.set_spec:
        params['set'] = args.set_spec

    print(f"Harvesting from: {args.url}")
    print(f"Prefix: {args.prefix}")
    if args.set_spec:
        print(f"Set: {args.set_spec}")

    # Harvest
    data = client.harvest(**params)

    # Save to file
    with open(args.output, 'w') as f:
        json.dump(data.dict, f, indent=2)

    print(f"Saved {len(data.dict.get('records', []))} records to {args.output}")


if __name__ == '__main__':
    main()
