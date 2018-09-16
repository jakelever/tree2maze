import argparse
import math
from collections import defaultdict
import svgwrite
import randomcolor

ABOVE,BELOW,LEFT,RIGHT = 1,2,3,4

def rev(l):
	return list(reversed(l))

def getChains(layer,active):
	assert isinstance(active,dict)
	startLocsToIndex = { locs:name for name,locs in active.items() }

	bottomLeft = -layer,-layer
	bottomRight = layer,-layer
	topLeft = -layer,layer
	topRight = layer,layer

	topEdge = [ (x,layer) for x in range(-layer+1,layer) ]
	bottomEdge = [ (x,-layer) for x in range(-layer+1,layer) ]
	leftEdge = [ (-layer,y) for y in range(-layer+1,layer) ]
	rightEdge = [ (layer,y) for y in range(-layer+1,layer) ]

	clockwiseSweep = [topLeft] + topEdge + [topRight] + rev(rightEdge) + [bottomRight] + rev(bottomEdge) + [bottomLeft] + leftEdge

	for startLoc in startLocsToIndex:
		assert startLoc in clockwiseSweep

	current = None
	#grid = {}
	chains = {}
	for x,y in clockwiseSweep + clockwiseSweep:
		if (x,y) in startLocsToIndex:
			tmp = startLocsToIndex[(x,y)]
			if tmp in chains:
				current = None
			else:
				current = tmp
				chains[current] = []

		if not current is None:
			#grid[(x,y)] = current
			chains[current].append((x,y))
			

	#print(chains)
	return chains

#	print(clockwiseSweep)


def chunked(iterable, n):
	chunksize = int(math.ceil(len(iterable) / n))
	return (iterable[i * chunksize:i * chunksize + chunksize] for i in range(n))

def nextGridPointOut(layer,x,y):
	if x==layer:
		return x+1,y
	elif x==-layer:
		return x-1,y
	elif y==layer:
		return x,y+1
	elif y==-layer:
		return x,y-1

	raise RuntimeError('Trying to get next grid point out with layer=%d with (%d,%d)' % (layer,x,y))

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Create a maze from a tree')
	parser.add_argument('--tree',required=True,type=str,help='Tab delimited file with source node name as first column and destination nodes (comma-delimited) as second column')
	parser.add_argument('--outSVG',required=True,type=str,help='SVG output of maze representation')
	args = parser.parse_args()

	seen = {'root'}
	tree = {}
	with open(args.tree) as f:
		for line in f:
			if line.startswith('#'):
				continue

			src,dsts = line.strip().split('\t')
			dsts = dsts.split(',')
			assert src in seen
			assert not src in tree
			tree[src] = dsts
			seen.update(dsts)

	#print(tree)

	grid = {}
	grid[(0,0)] = [BELOW]

	active,chars = {},{}
	active['root'] = (0,-1)
	chars['root'] = 'root'

	gridChars = {}

	dwg = svgwrite.Drawing(args.outSVG,profile='tiny')

	#startLocs = [(0,-1)]

	#getChains(1,[(0,-1),(0,1)])
	segments = defaultdict(list)
	segments['root'] = [(0,0)]

	for layer in range(1,5):
		chains = getChains(layer,active)
		
		doSplit = True

		for name,chain in chains.items():

			#for (x1,y1),(x2,y2) in zip(chain[:-1],chain[1:]):
				#dwg.add(dwg.line((x1,y1),(x2,y2)))
				#dwg.add(dwg.line((x1,y1),(x2,y2), stroke=svgwrite.rgb(10, 10, 16, '%')))
				#segments[name].append((x1,y1))
			#	segments[name].append((x2,y2))
			segments[name] += chain

			# Assign the characters to the grid
			#for x,y in chain:
			#	if chars[name]:
			#		gridChars[(x,y)] = chars[name][0]
			#		chars[name] = chars[name][1:]
			
			splitInto = 0
			if name in tree:
				splitInto = len(tree[name])

			#doSplit = (splitInto > 0)
			#if chars[name]:
			#	doSplit = False

				if len(chain) < (3*splitInto):
					doSplit = False

		for name,chain in chains.items():

			if name in tree:
				splitInto = len(tree[name])
				del active[name]
				del chars[name]

				subchains = list(chunked(chain,splitInto))
				print(subchains)
				for child,subchain in zip(tree[name],subchains):
					lastX,lastY = subchain[-1]
					newX,newY = nextGridPointOut(layer,lastX,lastY)
					active[child] = (newX,newY)
					#segments.append((lastX,lastY,newX,newY,child))
					segments[child].append((lastX,lastY))
					segments[child].append((newX,newY))
					print("Starting %s at (%d,%d)" % (child,lastX,lastY))
					chars[child] = child

			else:
				lastX,lastY = chain[-1]
				newX,newY = nextGridPointOut(layer,lastX,lastY)
				active[name] = (newX,newY)
				#segments.append((lastX,lastY,newX,newY,name))
				segments[child].append((lastX,lastY))
				segments[child].append((newX,newY))


		print(chains)
	

	#turtles = []
	#turtles.append( (0,-1,RIGHT) )
	for name,coords in segments.items():
		print(name, coords)

	minX = min ( x for name,coords in segments.items() for x,y in coords )
	maxX = max ( y for name,coords in segments.items() for x,y in coords )
	maxY = max ( y for name,coords in segments.items() for x,y in coords )

	rand_color = randomcolor.RandomColor()
	colors = defaultdict( lambda : rand_color.generate() )

	print(minX, maxX, maxY)

	dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), rx=None, ry=None, fill='rgb(0,0,0)'))
	if False:
		for name,coords in segments.items():
			for (x1,y1),(x2,y2) in zip(coords[:-1],coords[1:]):
				x1 = 10*(x1-minX)
				x2 = 10*(x2-minX)
				y1 = 10*(maxY-y1)
				y2 = 10*(maxY-y2)
				#coords = [ (10*(x-minX),10*(maxY-y)) for x,y in coords ]

				color = colors[name][0]
				#dwg.add(dwg.line((x1,y1),(x2,y2), stroke='rgb(255,255,255)', stroke_width=5))
				#dwg.add(dwg.line((x1,y1),(x2,y2), stroke=color, stroke_width=5))
				g = svgwrite.container.Group()
				#g.add(dwg.polyline(coords, stroke=color, stroke_width=5))
				g.add(dwg.line((x1,y1),(x2,y2), stroke=color, stroke_width=5))
				g.set_desc(name)
				dwg.add(g)
				#dwg.add(dwg.polygon(points, fill='rgb(255,255,255)'))
	else:	
		for name,coords in segments.items():
			coords = [ (10*(x-minX),10*(maxY-y)) for x,y in coords ]

			color = colors[name][0]
			g = svgwrite.container.Group()
			g.add(dwg.polyline(coords, stroke=color, stroke_width=5, fill='none'))
			g.set_desc(name)
			dwg.add(g)

	dwg.save()

