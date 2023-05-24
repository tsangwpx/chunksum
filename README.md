# chunksum

`chunksum` hashes a list of files by chunks. The default chunksize is 4G and algorithm SHA1. 

## Usage

```text
~$ python3 chunksum.py --help

usage: chunksum.py [-h] [--verbose] [--threads THREADS]
                   [--algorithm ALGORITHM] [--chunksize CHUNKSIZE]
                   inputs [inputs ...]

positional arguments:
  inputs

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         Increase the verbose level
  --threads THREADS
  --algorithm ALGORITHM
  --chunksize CHUNKSIZE
```

## Examples

```text
~$ python3 chunksum.py --threads 2 file1 file2

9c3898412e5f94be913b0f8b16154a0d8eb478ce file1#0 0x100000000+0
5ca34653eb647feecc44443687a17f87f0dc80fc file2#0 0x100000000+0
20364f19170e5a26dd117b517d54af9aa06048ad file1#1 0x100000000+100000000
4d86e1d4392b4498676a4ca32729e11f12533c3e file2#1 0x100000000+100000000
4c4be9106046722be0571e83e4ae8ce84847c828 file1#2 0x100000000+200000000
e77205a7ca2d5f6cec509c324cd0f231c47367df file2#2 0x100000000+200000000
1655361b6a1f68be20b6d8c9c415acdb8c8b84ba file1#3 0x100000000+300000000
e4e8a67da61d7ae1e22fbfeec7583fcee1e085b0 file2#3 0x100000000+300000000
2b8b1cd4f1ccdad4331f6271dc15a1a58819d7e5 file1#4 0x100000000+400000000
```
#### Format the chunksize as <NUMBER>G
```
~$ python3 chunksum.py DiskImage.img --threads 32 --chunksize 30G
```
## Sort the hashes

```text
~$ sort -Vk 2 CHUNKSUMS | sponge CHUNKSUMS
~$ sort -Vk 2 -o CHUNKSUMS CHUNKSUMS
```
