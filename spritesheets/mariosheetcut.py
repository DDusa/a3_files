from PIL import Image
im = Image.open("characters.png")
for i in range(0,6):
    region = (80+ 17*i ,34, 96+17*i,50)
    pic = im.crop(region)
    pic.save("mario" + str(i) +".png")
