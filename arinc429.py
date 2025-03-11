ON_GROUND = 0
ALTITUDE_CHANGE = 1
CRUISE = 2
ALTITUDE_MAX = 40000
SigBits = 15


def get_parity(x: int) -> int:
    result = 0
    while x:
        result ^= x & 1
        x >>= 1
    return result ^ 1
    # or return bin(x).count("1") % 2


def check_parity(x: int) -> str:
    return "Even" if get_parity(x) ^ 1 == 0 else "Odd"


def is_valid(x: int) -> bool:
    return get_parity(x >> 1) == x & 1


def reverse_bits(x: int, num_bits: int) -> int:
    return sum(((x >> i) & 1) << (num_bits - 1 - i) for i in range(num_bits))


def encode(label: int, sdi: int, data: int, ssm: int) -> int:
    label_bits = ((label // 100) << 6) | (((label // 10) % 10) << 3) | (label % 10)
    label_reversed = reverse_bits(label_bits, 8)

    result = label_reversed << 24
    result |= reverse_bits(sdi, 2) << 22
    result |= reverse_bits(data, 19) << 3
    result |= reverse_bits(ssm, 2) << 1

    result |= get_parity(result)

    return result


def decode(data: int):
    if not is_valid(data):
        return "Data is not valid"
    ssm = data >> 1 & 0xF
    data_out = data >> 3 & 0x7FFFF
    sdi = data >> 22 & 0xF
    label = data >> 24 & 0xFF
    ssm = reverse_bits(ssm, 2)
    data_out = reverse_bits(data_out, 19)
    sdi = reverse_bits(sdi, 2)
    label = reverse_bits(label, 8)
    label_out = (
        (label & 0x07) + ((label >> 3) & 0x07) * 10 + ((label >> 6) & 0x03) * 100
    )
    return label_out, sdi, data_out, ssm


def encode_001(altitude: int, state: int) -> (int, int):
    if altitude is None:
        return (1, state) if state == ON_GROUND else (0, 0)

    sign = 1 if altitude < 0 else 0
    altitude = abs(altitude)

    out = sign << (SigBits + 1)
    k = SigBits
    while altitude > 1 and k >= 0:
        step = ALTITUDE_MAX / (2 ** (SigBits - k))
        if altitude >= step:
            out |= 1 << k
            altitude -= step
        k -= 1

    out <<= 2

    if state in (ON_GROUND, ALTITUDE_CHANGE, CRUISE):
        out |= state
        return 3, out

    return 0, out


def decode_001(ssm: int, data: int) -> (int, int):
    if ssm == 0:
        return None, None
    if ssm == 1:
        return None, data  # data is only state in that case

    state = data & 3
    data >>= 2

    altitude = 0
    for k in range(SigBits + 1):
        altitude += (data & 1) * (ALTITUDE_MAX / (2 ** (SigBits - k)))
        data >>= 1

    if data:
        altitude = -altitude

    return altitude, state


def encode_002(rise_rate: float) -> (int, int):
    if rise_rate is None:
        return 1, 0
    ssm = 0
    if rise_rate < 0:
        ssm = 3
    rise_rate = abs(rise_rate)
    rise_rate_bits = (
        (int(rise_rate // 100) << 12)
        | ((int(rise_rate // 10) % 10) << 8)
        | (int(rise_rate % 10) << 4)
        | (int(rise_rate * 10) % 10)
    )
    return ssm, rise_rate_bits


def decode_002(ssm: int, data: int) -> float:
    if ssm == 1:
        return 0.0

    rise_rate = (
        (data & 0x0F)
        + ((data >> 4) & 0x0F) * 10
        + ((data >> 8) & 0x0F) * 100
        + ((data >> 12) & 0x0F) * 1000
    ) / 10
    if ssm == 3:
        rise_rate = -rise_rate
    return rise_rate



