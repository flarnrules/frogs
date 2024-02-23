
# layers = traits
flies = 8 #10
accessory = 12 #8
headgear = 20 #25
eyes = 10 #10
mouth = 26 #25
frog = 16 #20
lilypad = 4 #5
wildlife = 4 #10
water = 4 #8
background = 19 #12

total_traits = flies + accessory + headgear + eyes + mouth + frog + lilypad + wildlife + water + background

trait_combinations = flies * accessory * headgear * eyes * mouth * frog * lilypad * wildlife * water * background

percent = trait_combinations / 1071537984

print("total number of traits are {:,}".format(total_traits))
print("total possible trait combinations are {:,}".format(trait_combinations))
print("trait_combinations are {} of BAYC".format(percent))

# 159,667,200
# bayc had 1,071,537,984