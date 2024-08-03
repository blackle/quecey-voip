#!/usr/bin/env python3

words = []
def dictionary(name):
	with open(f'/usr/share/dict/{name}') as file:
		return list(
			filter(lambda word: all(letter in 'abcdefghijklmnopqrstuvwxyz' for letter in word),
				(line.strip() for line in file))
		)


words = set(dictionary('american-english-large') + dictionary('british-english-large'))
# You won't have nwl23 (NASPA Scrabble word list).
# This takes out most slurs.
# We intersect with it instead of using it directly to avoid copyright.
words = words.intersection(set(dictionary('nwl23')))

with open('en-large.txt', 'w') as file:
	for word in sorted(words):
		file.write(word + '\n')
