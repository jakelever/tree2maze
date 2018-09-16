import argparse
import math
from collections import defaultdict
import svgwrite
import randomcolor
import random

ABOVE,BELOW,LEFT,RIGHT = 1,2,3,4

def rev(l):
	return list(reversed(l))

def getSweepCoordinatesForLayer(layer):
	bottomLeft = -layer,-layer
	bottomRight = layer,-layer
	topLeft = -layer,layer
	topRight = layer,layer

	topEdge = [ (x,layer) for x in range(-layer+1,layer) ]
	bottomEdge = [ (x,-layer) for x in range(-layer+1,layer) ]
	leftEdge = [ (-layer,y) for y in range(-layer+1,layer) ]
	rightEdge = [ (layer,y) for y in range(-layer+1,layer) ]

	clockwiseSweep = [topLeft] + topEdge + [topRight] + rev(rightEdge) + [bottomRight] + rev(bottomEdge) + [bottomLeft] + leftEdge

	return clockwiseSweep

def sweepAroundLayer(layer,active,clockwiseProb):
	# For each layer, sweep around and assign each grid point to an active path

	assert isinstance(active,dict)
	startLocsToIndex = { locs:name for name,locs in active.items() }

	clockwiseSweep = getSweepCoordinatesForLayer(layer)

	for startLoc in startLocsToIndex:
		assert startLoc in clockwiseSweep

	current = None
	paths = {}

	sweep = clockwiseSweep
	if random.random() > clockwiseProb:
		sweep = rev(clockwiseSweep)

	# Sweep around twice in case we miss anything
	for x,y in sweep + sweep:

		# If the current location is on an active path, start tracking this path
		if (x,y) in startLocsToIndex:
			tmp = startLocsToIndex[(x,y)]
			if tmp in paths:
				current = None # But ignore if we've already done this path
			else:
				current = tmp
				paths[current] = []

		# Add this location to the currently tracked path
		if not current is None:
			paths[current].append((x,y))

	return paths

def chunked(iterable, n):
	# Chunk up a list into n roughly equal sized chunks
	chunksize = int(math.ceil(len(iterable) / n))
	return (iterable[i * chunksize:i * chunksize + chunksize] for i in range(n))

def nextGridPointOut(layer,x,y):
	# Figure out the corresponding grid point on the next layer outwards

	if x==layer:
		return x+1,y
	elif x==-layer:
		return x-1,y
	elif y==layer:
		return x,y+1
	elif y==-layer:
		return x,y-1

	raise RuntimeError('Trying to get next grid point out with layer=%d with (%d,%d)' % (layer,x,y))

def loadTree(filename):
	# Load a tree from a two-column file

	seen = {'root'}
	tree = {}
	with open(filename) as f:
		for line in f:
			line = line.strip()
			if line.startswith('#') or line == '':
				continue

			parent,children = line.split('\t')
			children = children.split(',')

			assert parent in seen, "Parent must already be a child or 'root' (%s)" % parent
			assert not parent in tree, "Parent must already be a child or 'root' (%s)" % parent
			assert len(children) == len(set(children)), "Children must have unique names (%s)" % children

			tree[parent] = children
			seen.update(children)

	return tree

def treeToDot(tree,outFilename,colors):
	with open(outFilename,'w') as outF:
		outF.write("digraph tree {\n")
		for parent,children in tree.items():
			for child in children:
				outF.write("%s -> %s [color=\"%s\"];\n" % (parent.replace(' ','_'),child.replace(' ','_'),colors[child]))
		for node,color in colors.items():
			outF.write("%s [color=\"%s\"];\n" % (node.replace(' ','_'),color))
		outF.write("}\n")


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Create a maze from a tree')
	parser.add_argument('--debug',action='store_true',help='Add some debug information')
	parser.add_argument('--seed',required=False,type=int,help='Seed for randomness')
	parser.add_argument('--clockwiseProb',required=False,type=float,default=0.5,help='Chance of the spiral going clockwise at each layer (0.0-1.0)')
	parser.add_argument('--extendProb',required=False,type=float,default=0.2,help='Chance of just extending a path without ending (0.0-1.0)')
	parser.add_argument('--textmode',required=False,type=str,default='simple',help='Whether to display the path name along the path (path), simply at the start (simple) or not at all (none)')
	parser.add_argument('--tree',required=True,type=str,help='Tab delimited file with source node name as first column and destination nodes (comma-delimited) as second column')
	parser.add_argument('--outSVG',required=True,type=str,help='SVG output of maze representation')
	parser.add_argument('--outDot',required=False,type=str,help='DOT output of tree')
	parser.add_argument('--minLayers',required=False,type=int,help='Whether to put a lower-limit on the number of layers, or just wait until tree has been fully realised')
	parser.add_argument('--maxLayers',required=False,type=int,help='Whether to put an upper-limit on the number of layers, or just wait until tree has been fully realised')
	args = parser.parse_args()

	assert args.clockwiseProb >= 0.0 and args.clockwiseProb <= 1.0
	assert args.extendProb >= 0.0 and args.extendProb <= 1.0
	assert args.textmode in ['path','simple','none']

	tree = loadTree(args.tree)

	if args.seed:
		random.seed(args.seed)
	else:
		random.seed()

	grid = {}
	grid[(0,0)] = [BELOW]

	active,chars = {},{}
	active['root'] = (0,-1)

	dwg = svgwrite.Drawing(args.outSVG,profile='tiny')

	segments = defaultdict(list)
	segments['root'] = [(0,0)]

	for layer in range(1,50):

		# First some logic of whether we should stop as we've got enough layers, got too many layers and whether the tree is completely drawn (e.g. fully navigated)
		if args.maxLayers and layer > args.maxLayers:
			print("Past maximum layers. Stopping")
			break

		treeComplete = not any ( name in tree for name in active )

		if args.minLayers:
			if layer >= args.minLayers and treeComplete:
				print("Past minimum layers and tree complete. Stopping")
				break
		elif treeComplete:
			print("Tree complete. Stopping")
			break

		print ("Generating layer %d" % layer)

		paths = sweepAroundLayer(layer,active,args.clockwiseProb)

		for name,path in paths.items():
			# Decide if there is space to do a move down the tree this layer (if it is not even needed)
			moveDownTree = True
			splitInto = 0
			if name in tree:
				splitInto = len(tree[name])

				if len(path) < (2*splitInto):
					moveDownTree = False

			justExtendIt = (random.random() < args.extendProb)

			if moveDownTree and name in tree:
				if args.debug:
					print("Budding Children", name)

				# Split the section of path on this layer into the number of children and branch off after each subpath
				splitInto = len(tree[name])
				del active[name]

				subpaths = list(chunked(path,splitInto))
				for i,(child,subpath) in enumerate(zip(tree[name],subpaths)):
					isLast = (i == (len(subpaths)-1))

					if isLast:
						if i > 0:
							segments[child] = [subpaths[i-1][-1]]
						segments[child] += subpath
					else:
						segments[name] += subpath

					lastX,lastY = subpath[-1]
					newX,newY = nextGridPointOut(layer,lastX,lastY)
					active[child] = (newX,newY)
					segments[child].append((lastX,lastY))
					segments[child].append((newX,newY))
					chars[child] = child

			elif justExtendIt or name in tree:
				# Or just add the full path for this active layer and setup for the next layer
				if args.debug:
					print('Extending',name)

				segments[name] += path


				lastX,lastY = path[-1]
				newX,newY = nextGridPointOut(layer,lastX,lastY)
				active[name] = (newX,newY)
				segments[name].append((lastX,lastY))
				segments[name].append((newX,newY))
			else:
				if args.debug:
					print('Ending',name)
				segments[name] += path
				del active[name]


	print ("Paths:")
	for name,coords in segments.items():
		print(name, coords)

	# Get some min and max coordinates for scaling
	minX = min ( x for name,coords in segments.items() for x,y in coords )
	maxX = max ( y for name,coords in segments.items() for x,y in coords )
	maxY = max ( y for name,coords in segments.items() for x,y in coords )

	# Set up colors
	rand_color = randomcolor.RandomColor()
	nodes = list(set(list(tree.keys()) + sum(tree.values(),[])))
	colors = { name:rand_color.generate()[0] for name in nodes }

	# Add a black background
	dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), rx=None, ry=None, fill='rgb(0,0,0)'))

	# Get each path
	textgroup = svgwrite.container.Group()
	textgroup.set_desc('text')

	for name,coords in segments.items():
		# Scale the coordinates
		coords = [ (100*(x-minX),100*(maxY-y)) for x,y in coords ]

		# Add coordinates as a colored polyline with a name
		color = colors[name]
		g = svgwrite.container.Group()
		g.add(svgwrite.shapes.Polyline(coords, stroke=color, stroke_width=50, fill='none'))
		g.set_desc(name)
		dwg.add(g)

		# Add the text name for the path
		if not args.textmode == 'none':
			if args.textmode == 'path':
				pathCommand = "M%f,%f" % (coords[0][0],coords[0][1])
				for x,y in coords[1:]:
					pathCommand += " L%f,%f" % (x,y)
				textpath = svgwrite.path.Path(d=pathCommand,fill='none')
				text = svgwrite.text.Text("",font_size="25px")
				text.add(svgwrite.text.TextPath(path=textpath, text=name, startOffset=10, method='align', spacing='exact'))
				textgroup.add(textpath)
				textgroup.add(text)
			elif args.textmode == 'simple':
				text = svgwrite.text.Text(name,insert=coords[1],font_size="25px")
				textgroup.add(text)
				

	if not args.textmode == 'none':
		dwg.add(textgroup)

	dwg.save()

	if args.outDot:
		treeToDot(tree,args.outDot,colors)

	print("LAYER_COUNT=%d" % maxY)

