# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import arinc429

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print(bin(arinc429.encode(325, 2, 1902, 3)))
    print(arinc429.check_parity(arinc429.encode(325, 1, 2, 3)))
    print_hi('Thibaut')
    word = 0b01100000000000000000000000000110  # Example ARINC 429 word
    print(arinc429.check_parity(word))
    print(arinc429.is_valid(word))
    print(arinc429.decode(arinc429.encode(325, 2, 1902, 3)))

    ssm, data = arinc429.encode_001(-30000, arinc429.CRUISE)
    print(bin(ssm), bin(data))
    altitude, state = arinc429.decode_001(ssm, data)
    print(altitude, state)


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
