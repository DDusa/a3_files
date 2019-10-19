from PIL import Image
im = Image.open("spritesheets/enemies.png")
for i in range(0,3):
    region = (16*i,16,16+16*i,32)
    pic = im.crop(region)
    pic.save("images/mushroom" + str(i) +".png")
