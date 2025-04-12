ON_GROUND = 0
ALTITUDE_CHANGE = 1
CRUISE = 2
ALTITUDE_MAX = 40000
SigBits = 15


class ARINC429:
    ON_GROUND = 0
    ALTITUDE_CHANGE = 1
    CRUISE = 2
    ALTITUDE_MAX = 40000
    SigBits = 15

    @staticmethod
    def __get_parity(x: int) -> int:
        result = 0
        while x:
            result ^= x & 1
            x >>= 1
        return result ^ 1
        # or return bin(x).count("1") % 2

    @staticmethod
    def check_parity(x: int) -> str:
        return "Even" if ARINC429.__get_parity(x) ^ 1 == 0 else "Odd"

    @staticmethod
    def is_valid(x: int) -> bool:
        return ARINC429.__get_parity(x >> 1) == x & 1


    @staticmethod
    def __reverse_bits(x: int, num_bits: int) -> int:
        return sum(((x >> i) & 1) << (num_bits - 1 - i) for i in range(num_bits))

    @staticmethod
    def __encode_001(altitude: int, state: int) -> (int, int):
        if altitude is None:
            return (1, state) if state == ON_GROUND else (0, 0)
        if abs(altitude) > ALTITUDE_MAX:
            return 0, 0
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


    @staticmethod
    def __decode_001(ssm: int, data: int) -> (int, int):
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


    @staticmethod
    def __encode_002(rise_rate: float) -> (int, int):
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

    @staticmethod
    def __decode_002(ssm: int, data: int) -> float | None:
        if ssm == 1:
            return None

        rise_rate = (
                            (data & 0x0F)
                            + ((data >> 4) & 0x0F) * 10
                            + ((data >> 8) & 0x0F) * 100
                            + ((data >> 12) & 0x0F) * 1000
                    ) / 10
        if ssm == 3:
            rise_rate = -rise_rate
        return rise_rate

    @staticmethod
    def __encode_003(angle: float) -> (int, int):
        if angle is None:
            return 1, 0
        ssm = 0
        if angle < 0:
            ssm = 3
        angle = abs(angle)
        angle_bits = (
                (int(angle // 10) << 8) | (int(angle % 10) << 4) | (int(angle * 10) % 10)
        )
        return ssm, angle_bits

    @staticmethod
    def __decode_003(ssm: int, data: int) -> float | None:
        if ssm == 1:
            return None
        angle = ((data & 0x0F) + ((data >> 4) & 0x0F) * 10 + ((data >> 8) & 1) * 100) / 10
        if ssm == 3:
            angle = -angle
        return angle

    @staticmethod
    def __encode_004(pwr: float) -> (int, int):
        if pwr is None:
            return 1, 0
        ssm = 0
        if pwr < 0:
            ssm = 3
        pwr = abs(pwr)
        pwr_bits = (
            ((int(pwr // 100) & 0x07)<< 16) | ((int(pwr // 10) % 10)<< 12) | (int(pwr % 10) << 8) | ((int(pwr * 10) % 10) << 4) |
                    (int(pwr * 100) % 10)
        )

        return ssm, pwr_bits

    @staticmethod
    def __decode_004(ssm: int, data: int) -> float | None:
        if ssm == 1:
            return None
        pwr = ((data & 0x0F) + ((data >> 4) & 0x0F) * 10 + ((data >> 8) & 0x0F) * 100 + ((data >> 12) & 0x0F) * 1000 + ((data >> 16) & 0x07) * 10000) / 100
        if ssm == 3:
            pwr = -pwr
        return pwr

    __encodes = [__encode_001, __encode_002, __encode_003, __encode_004]
    __decodes = [__decode_001, __decode_002, __decode_003, __decode_004]

    @staticmethod
    def encode(label: int, sdi: int, *args) -> int:
        if label - 1 not in range(len(ARINC429.__encodes)):
            return 1

        ssm, data = ARINC429.__encodes[label - 1](*args)

        label_bits = ((label // 100) << 6) | (((label // 10) % 10) << 3) | (label % 10)
        label_reversed = ARINC429.__reverse_bits(label_bits, 8)

        result = label_reversed << 24
        result |= ARINC429.__reverse_bits(sdi, 2) << 22
        result |= ARINC429.__reverse_bits(data, 19) << 3
        result |= ARINC429.__reverse_bits(ssm, 2) << 1

        result |= ARINC429.__get_parity(result)

        return result

    @staticmethod
    def decode(data: int) -> list:
        if not ARINC429.is_valid(data):
            return [None]
        ssm = data >> 1 & 0xF
        data_out = data >> 3 & 0x7FFFF
        sdi = data >> 22 & 0xF
        label = data >> 24 & 0xFF
        ssm = ARINC429.__reverse_bits(ssm, 2)
        data_out = ARINC429.__reverse_bits(data_out, 19)
        sdi = ARINC429.__reverse_bits(sdi, 2)
        label = ARINC429.__reverse_bits(label, 8)
        label_out = (
                (label & 0x07) + ((label >> 3) & 0x07) * 10 + ((label >> 6) & 0x03) * 100
        )
        if label_out - 1 not in range(len(ARINC429.__decodes)):
            return [None]

        out = ARINC429.__decodes[label_out - 1](ssm, data_out)

        return [label_out, sdi, ssm, out]
