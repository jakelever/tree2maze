# tree2maze

This is a Python tool to transform a tree into a maze. Because why not!

## Installation

This requires Python3 and the following libraries: svgwrite and randomcolor.

```
pip install svgwrite randomcolor
```

## Usage

It expects an input of a tree file formatted as a TSV. The first column is the name of the parent node and the second column to a comma-delimited list of the child nodes. e.g.

```
root	fruit,vegetable
fruit	apple,orange,strawberry
vegetable	carrot,lettuce
apple	granny smith,red delicious
carrot	orange carrot
```

Then usage is below:

```
python tree2maze.py --tree example_tree.tsv --outSVG example_maze.svg
```

Additional flags are:

- --outDot : Output a Graphviz dot file to generate a simple tree structure with edges colored
- --minLayers : Set a minimum number of layers to create for the maze
- --maxLayers : Set a maximum number of layers (tree may be incomplete)

