import string
import random
def CreateMachineNumber():
    charlength = random.randint(2, 10)

    result = ''.join(random.choices(string.ascii_uppercase + string.digits, k=charlength))

    hifunnum = random.randint(0, 1)
    hifunset = set()
    for i in range(hifunnum):
        hifunset.add(random.randint(1, charlength - 1))

    for i in hifunset:
        result = result[:i] + "-" + result[i:]

    print(result)  # 出力例 H2cEc
    return result