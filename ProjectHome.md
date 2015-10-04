This project tries to implement an easy way to organize files (and any other uris) by labeling them (tagging).

What makes different this project is that, in addition to files (uris), **labels** **can** **also** **be** **labeled** **with** **other** **labels**, creating a Directed Graph of labels and uris. So you can create a label hierarchy (tag hierarchy).

Labelfs also provides a way to be used with the traditional hierarchic filesystem commands  (mkdir, mv, ls, ln,...) or graphical managers (nautilus,...), implementing a logical layer on top of hierarchical filesystem (with python-fuse).

Additionally, the label-engine can be imported as a module or queried as a platform. It has it's own gramatics to perform operations with files (uris) and other labels (similar to CSS Selectors). This specific gramatics can be used also through traditional commands.

Welcome cooperation!!

UserGuide

Screenshots: http://labels-project.blogspot.com/