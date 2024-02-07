
# layers = traits
flies = 10 #10
accessory = 8 #8
headgear = 25 #25
eyes = 10 #10
mouth = 25 #25
frog = 20 #20
lilypad = 5 #5
wildlife = 10 #10
water = 8 #8
background = 12 #12

total_traits = flies + accessory + headgear + eyes + mouth + frog + lilypad + wildlife + water + background

trait_combinations = flies * accessory * headgear * eyes * mouth * frog * lilypad * wildlife * water * background

percent = trait_combinations / 1071537984

print(total_traits)
print(trait_combinations)
print("trait_combinations are {} of BAYC".format(percent))

# 48,000,000,000
# bayc had 1,071,537,984