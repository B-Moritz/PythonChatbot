
prompt = 'Add the hidden word: '
inputStr = input(prompt).lower()
print ('\u001b[1A' + prompt + '\u011b[K')