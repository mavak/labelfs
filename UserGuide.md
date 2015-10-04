# Introduction #

Labelfs is like a file-system, but with URIs. It's a URI-system.

With labelfs, you can organize your URIs in a Directed Graph.

In addition to files, URIs can also be labels.

You can attach URIs onto other URIs (think of labeling or tagging) creating a Directed Graph of URIs.

Labelfs can be queried, via fuse, through traditional hierarchical commands (ls, mkdir, ln, cp, mv, ...) and GUIs (nautilus,...), or using the "Labels" application (GTK).


# Quick Start Guide #

(Tested in Ubuntu 11.10)

## Setup and launch ##

### Graphical UI ###

0. (recommended) Install this font: http://www.dafont.com/impact-label.font

1. Start Labels app
```
~/labelfs/labels/labels.py
```

### FUSE ###

0. Install python-fuse package

```
sudo apt-get install python-fuse
```

1. Create the mount point

```
mkdir ~/Labels
```

2. Mount the filesystem

```
~/labelfs/lfsfuse.py ~/Labels
```

(to umount do: fusermount -u ~/Labels)


## Usage ##

### Graphical UI ###

(Is an experiment. My idea is to do de action label files and any other URI like using an old labeler, perhaps by selecting a group of labels and visually attach them to the mouse pointer)

Start dragging some files from nautilus

### FUSE ###

You can start by adding your files to the new filesystem

```
ln -s ~/Music ~/Labels
```

```
ln -s ~/Documents ~/Labels
```

View the results in your file manager (eg. nautilus).
Folders are now labels! (the icon is the same, I know...)
Drag'n'drop (to nautilus) is partially supported. Omit all errors and warnings!! (I'm still wondering what to do with the URI-graph when files and files are created, moved, linked, ...)

#### Experimental features ####

Experiment in nautilus by creating folders (=labels)

Create new files and labels with traditional hierarchic commands.
Examples:

```
mkdir ~/Labels/newlabel
```

```
touch ~/Labels/newlabel/file
```

```
cp /path/to/a/file ~/Labels
```

```
cp ~/Labels/file1 ~/Labels/file2
```

Attach labels to files by moving the files to a path of labels:

```
mv ~/Labels/file ~/Labels/newlabel
```

Attach labels to other labels by moving them too:

```
mv ~/Labels/old/path/to/label ~/Labels/new/path/to/label
```

(labels in old path will also be removed from label)

Remove labels with `rmdir`, #TODO

##### Query through commands #####

Use **labelfs** **language** to do complex operations and queries.

With `ls` you can perform queries. Put the query before the path "/query/"


```
ls ~/Labels/query/"label1"+>"file1"'
```

(will attach label1 onto file1)

```
ls ~/Labels/query/"label1"+>"label2"
```

(will attach label1 onto label2)

```
ls ~/Labels/query/"label1"->"file1"
```

(will remove label1 from file1)

```
ls ~/Labels/query/*->"file1"'
```

(will remove all labels from file1)

```
ls ~/Labels/query/file:["label1" > *]'
```

(will list all files labeled with label1)

Complex operations wtih logical operators are allowed.

## Labelfs Query Language Specification ##

(similar to CSS Selectors http://www.w3.org/TR/CSS2/selector.html)

GRAMMAR
```
expr   ->  expr | term | expr - term | term
term   ->  term * fact | term & fact | fact
fact   ->  fact > nodes | nodes [+> ->] nodes | nodes
nodes  ->  (expr) | ^nodes | [@ X R +R -R] nodes | scheme:nodes | name | *
```

|uri|`"`_`uri`_`"`|Matches any URI with uri or name equal to _`uri`_|
|:--|:------------|:------------------------------------------------|
|scheme|_`scheme`_`:`|Matches URIs of scheme _`scheme`_                |

|create|`@`|`@` _`uris`_|Creates _`uris`_|
|:-----|:--|:-----------|:---------------|
|delete|`X`|`X` _`uris`_|Deletes _`uris`_|
|root  |`R`|`R` _`uris`_|Matches all _`uris`_ that are Root|
|set root|`+R`|`+R` _`uris`_|Set _`uris`_ as Root|
|unset root|`-R`|`-R` _`uris`_|Unset _`uris`_ as Root|
|child |`>`|_`parents`_ `>` _`childs`_|Matches all _`childs`_ that are childs of _`parents`_|
|parent|`<`|_`childs`_ `<` _`parents`_|Matches all _`parents`_ that are parents of _`childs`_|
|add   |`+>`|_`parents`_ `+>` _`childs`_|Add _`parents`_ to _`childs`_|
|remove|`->`|_`parents`_ -> _`childs`_|Remove _`parents`_ from _`childs`_|

|not|`^`|`^`_`uris`_|Matches all URIs that are not _`uris`_|
|:--|:--|:----------|:-------------------------------------|
|all|`*`|`*`        |Matches all URIs                      |
|intersect|`&`|_`uris1`_ `&` _`uris2`_|matches URIs that are in _`uris1`_ AND _`uris2`_|
|union| `|` |_`uris1`_ `|` _`uris2`_|matches URIs that are in _`uris1`_ OR _`uris2`_|

Use brackets `[`  `]` to group the operations