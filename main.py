# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from arinc429 import ARINC429

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    print(bin(ARINC429.encode(325, 2, 1902, 3)))
    print(ARINC429.check_parity(ARINC429.encode(325, 1, 2, 3)))
    print_hi('Thibaut')
    word = 0b01100000000000000000000000000110  # Example ARINC 429 word
    print(ARINC429.check_parity(word))
    print(ARINC429.is_valid(word))
    print(ARINC429.encode(1, 2, 300000, ARINC429.ON_GROUND))
    print(ARINC429.is_valid(ARINC429.encode(1, 2, 300000, ARINC429.ON_GROUND)))
    print(ARINC429.decode(int(ARINC429.encode(1, 2, 3000, ARINC429.CRUISE))))
    print(ARINC429.decode(2151677953))


    print(ARINC429.encode(4, 2, 100))
    print(ARINC429.decode(ARINC429.encode(4, 2, -799.99)))

    # ssm, data = ARINC429.encode_001(-30000, ARINC429.CRUISE)
    # print(bin(ssm), bin(data))
    # altitude, state = ARINC429.decode_001(ssm, data)
    # print(altitude, state)
    #
    # ssm, data = ARINC429.encode_002(-391.2)
    # print(bin(ssm), bin(data))
    # rate = ARINC429.decode_002(ssm, data)
    # print(rate)
    #
    # ssm, data = ARINC429.encode_003(-2.1)
    # print(bin(ssm), bin(data))
    # word = ARINC429.encode(3, 1, data, ssm)
    # print(bin(word))
    # print(ARINC429.is_valid(word))
    # label, sdi, data, ssm = ARINC429.decode(word)
    # print(label, sdi)
    # print(ARINC429.decode_003(ssm, data))

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
