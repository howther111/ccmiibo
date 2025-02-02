import random
def CreatePetName():

    firstchars = list("アイウエオカキクケコサシスセソタチツテトナニヌネノ" +
                 "ハヒフヘホマミムメモヤユヨラリルレロワ" +
                 "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ")

    chars = list("アイウエオカキクケコサシスセソタチツテトナニヌネノ" +
                 "ハヒフヘホマミムメモヤユヨラリルレロワンー" +
                 "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ" +
                 "ァィゥェォッャュョ")

    charlength = random.randint(1, 7)


    result = ''.join(random.choices(chars, k=charlength))
    result = random.choice(firstchars) + result

    print(result)
    return result