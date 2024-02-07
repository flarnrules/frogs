
# layers = traits
flies = 8 #10
accessory = 5 #8
headgear = 20 #25
eyes = 6 #10
mouth = 21 #25
frog = 11 #20
lilypad = 2 #5
wildlife = 2 #10
water = 4 #8
background = 9 #12

total_traits = flies + accessory + headgear + eyes + mouth + frog + lilypad + wildlife + water + background

trait_combinations = flies * accessory * headgear * eyes * mouth * frog * lilypad * wildlife * water * background

percent = trait_combinations / 1071537984

print(total_traits)
print(trait_combinations)
print("trait_combinations are {} of BAYC".format(percent))

# 159,667,200
# bayc had 1,071,537,984