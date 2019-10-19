from PIL import Image
im = Image.open("spritesheets/items.png")
for i in range(0,4):
    region = (16*i,112,16+16*i,128)
    pic = im.crop(region)
    pic.save("images/spinning_coin" + str(i) +".png")
