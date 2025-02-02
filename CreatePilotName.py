import random
def CreatePilotName():

    firstchars = list("アイウエオカキクケコサシスセソタチツテトナニヌネノ" +
                 "ハヒフヘホマミムメモヤユヨラリルレロワ" +
                 "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ")

    chars = list("アイウエオカキクケコサシスセソタチツテトナニヌネノ" +
                 "ハヒフヘホマミムメモヤユヨラリルレロワンー" +
                 "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ" +
                 "ァィゥェォッャュョ")

    charlength = random.randint(0, 6)


    result = ''.join(random.choices(chars, k=charlength))
    result = random.choice(firstchars) + result

    print(result)
    return result