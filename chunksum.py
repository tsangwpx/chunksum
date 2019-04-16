"""
Hash files by chunks parallelly

Aaron Tsang
MIT License
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import dataclasses
import hashlib
import logging
import os.path
import re
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Awaitable, Dict, List, Tuple, Optional

_logger = logging.getLogger(__name__)


def parse_binary_number(value):
    match = re.match(r'^(?P<size>[1-9][0-9]*)(?:(?P<unit>[kmgtpezy])b?)?$', value, re.IGNORECASE)

    if not match:
        raise ValueError(value)

    size = int(match.group('size'))
    multiplier = {
        'k': 1024,
        'm': 1024 ** 2,
        'g': 1024 ** 3,
        't': 1024 ** 4,
        'p': 1024 ** 5,
        'e': 1024 ** 6,
        'z': 1024 ** 7,
        'y': 1024 ** 8,
    }.get(match.group('unit').lower(), 1)

    assert isinstance(multiplier, int) and multiplier >= 1
    return size * multiplier


def parse():
    p = ArgumentParser()
    p.add_argument('--verbose', '-v', action='count', default=0,
                   help='Increase the verbose level')
    p.add_argument('--threads', type=int, default=4)
    p.add_argument('--algorithm', type=str, default='sha1')
    p.add_argument('--chunksize', type=parse_binary_number, default='4G')
    p.add_argument('inputs', nargs='+')
    ns = p.parse_args()
    return ns


@dataclass
class FileEntry:
    path: str
    size: int
    chunksize: int
    nchunks: int = dataclasses.field(init=False)

    def __post_init__(self):
        q, r = divmod(self.size, self.chunksize)
        self.nchunks = q + (1 if r else 0)


@dataclass
class FileHashes:
    path: str
    hashes: List[Optional[bytes]]


def compute_hash(algo, entry: FileEntry, chunk_id: int):
    constructor = getattr(hashlib, algo, None)

    if constructor is None or True:
        md = hashlib.new(algo)
    else:
        md = constructor()

    offset, length = chunk_range(entry.size, entry.chunksize, chunk_id)
    _logger.debug('%s chunk_id=%d, offset=%d, length=%d', entry.path, chunk_id, offset, length)

    with open(entry.path, 'rb', buffering=0) as handle:
        buf = bytearray(1024 * 1024 * 32)

        handle.seek(offset)
        count = 0

        while count < length:
            nread = handle.readinto(buf)
            if not nread:
                raise ValueError(nread)
            md.update(buf[:nread])
            count += nread

        # import mmap
        # mm = mmap.mmap(handle.fileno(), length, prot=mmap.PROT_READ, offset=offset)
        # md.update(mm[:])
        # del mm

    del handle

    return entry.path, chunk_id, md.digest()


def chunk_range(size, chunksize, chunk_id):
    assert size >= 0
    assert chunksize >= 1
    assert chunk_id >= 0

    offset = chunk_id * chunksize

    assert offset < size

    length = chunksize
    if offset + length > size:
        length = size - offset

    return offset, length


async def main():
    ns = parse()
    assert isinstance(ns.threads, int) and ns.threads >= 1

    logging.root.handlers[:] = ()
    if ns.verbose >= 2:
        logging.basicConfig(level=logging.DEBUG)
    elif ns.verbose >= 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig()

    _logger.debug('%r', ns)

    chunksize = ns.chunksize
    assert chunksize >= 1
    assert chunksize % (64 * 1024) == 0

    if ns.algorithm not in hashlib.algorithms_available:
        raise ValueError(f'Algorithm {ns.algorithm} is not supported')

    entries: Dict[str, FileEntry] = {s: FileEntry(s, os.path.getsize(s), ns.chunksize) for s in ns.inputs}
    hashes: Dict[str, FileHashes] = {s: FileHashes(s, [None] * entries[s].nchunks) for s in ns.inputs}

    loop = asyncio.get_running_loop()
    tasks = []

    # Seem that ThreadPoolExecutor is good enough
    # ProcessPoolExecutor probably bounded by IO
    with concurrent.futures.ThreadPoolExecutor(ns.threads) as pool:
        # with concurrent.futures.ThreadPoolExecutor(8) as pool:
        def generator():
            nonlocal path, entry, chunk_id
            for path, entry in entries.items():
                for chunk_id in range(entry.nchunks):
                    yield path, chunk_id

        for path, chunk_id in sorted(generator(), key=lambda s: s[::-1]):
            entry = entries.get(path)
            tasks.append(loop.run_in_executor(
                pool, compute_hash,
                ns.algorithm, entry, chunk_id,
            ))
        #
        # for path, entry in entries.items():
        #     for chunk_id in range(entry.nchunks):
        #         tasks.append(loop.run_in_executor(
        #             pool, compute_hash,
        #             ns.algorithm, entry, chunk_id))

        for future in asyncio.as_completed(tasks):  # type: Awaitable[Tuple[str, int, bytes]]
            path, chunk_id, h = await future
            hashes[path].hashes[chunk_id] = h
            entry = entries[path]
            offset, length = chunk_range(entry.size, entry.chunksize, chunk_id)

            _logger.info('hash(%s#%d) = %s', path, chunk_id, h.hex())
            print(f'{h.hex()} {path}#{chunk_id:d} 0x{length:x}+{offset:x}', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
