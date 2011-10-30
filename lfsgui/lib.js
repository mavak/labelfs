var Stts=[];
var Evts=[];
var Elms=[];

//Element handling
function createElement(a){
  if(('name' in a)){ //que tal posar un name i attr_id automatic???
    if(!('parent' in a)){ parent = document.getElementsByTagName("body")[0];}
    else{parent = Elms[a.parent]}
    if(!('attrs' in a)){ a.attrs = {}; }
    arrayp=a.name.split("#");
    if(arrayp[0] != ""){
      Elms[a.name] = document.createElement(arrayp[0]);
      if(arrayp[1] != ""){ Elms[a.name].setAttribute("id",arrayp[1]); }
      for(attr in a.attrs){
        if(attr == 'class'){
          var classes=a.attrs[attr].split(' ');
          for (var i=0; i<classes.length; i++) {
            if(classes[i][0] == '-'){
              $(Elms[a.name]).removeClass(classes[i].substring(1));
            }else{
              $(Elms[a.name]).addClass(classes[i]);
            }
          }
        }else{
          Elms[a.name].setAttribute(attr,a.attrs[attr]);
        }
      }
      parent.appendChild(Elms[a.name]);
    }
  }
}

function removeChilds(element){
  if(element.hasChildNodes()){
    while ( element.childNodes.length >= 1 ){
      removeChilds( element.firstChild );       
    } 
  }
  if(element.parentNode != undefined){
    element.parentNode.removeChild(element);
  } //else ??????????????????????????
}

function remove(a){
  if('name' in a){
    if(a.name in Elms){
      removeChilds(Elms[a.name]);
      delete Elms[a.name];
    }
  }
}

function createTextNode(a){
  Elms[a.name] = document.createElement('SPAN');
  Elms[a.name].innerHTML = a.text;
  if(!('parent' in a)){ parent = document.getElementsByTagName("body")[0];}
  else{parent = Elms[a.parent]}
  parent.appendChild(Elms[a.name]);
}

function set(a){
  if('text' in a){
    remove(a);
    createTextNode(a);
  }else if((a.name in Elms) && $(Elms[a.name])){
    if('parent' in a){
      var actpare= Elms[a.name].parentNode;
      if(actpare != undefined){
        actpare.removeChild(Elms[a.name]);
      }
      Elms[a.parent].appendChild(Elms[a.name]);
    }
    if('attrs' in a){
      for(attr in a.attrs){
        if(attr == 'class'){
          var classes=a.attrs[attr].split(' ');
          for (var i=0; i<classes.length; i++) {
            if(classes[i][0] == '-'){
              $(Elms[a.name]).removeClass(classes[i].substring(1));
            }else{
              $(Elms[a.name]).addClass(classes[i]);
            }
          }
        }else{
          Elms[a.name].setAttribute(attr,a.attrs[attr]);
        }
      }
    }
  }else{
    createElement(a);
  }
}

//Event handling
var CustomEvent = function() {
	this.eventName = arguments[0];
	var mEventName = this.eventName;

	var eventActions = [];

	this.subscribe = function(fn) {
		eventActions.push(fn);
	};

	this.publish = function(sender, eventArgs) {
		if(eventActions != null) {
      for (var i=0; i<eventActions.length; i++) {
        eventActions[i](sender, eventArgs);
      }
		}
	};
};

function subscribe(eventnames,func){
  for (var i=0; i<eventnames.length; i++) {
    if(!(eventnames[i] in Evts)){
      Evts[eventnames[i]] = new CustomEvent(eventnames[i]);
    }
    Evts[eventnames[i]].subscribe(func);
  }
}

function fire(eventnames){
  for (var i=0; i<eventnames.length; i++) {
    if(eventnames[i] in Evts){
      Evts[eventnames[i]].fire();
    }
  }
}

//labelfs-engine
function lfsquery(query,func){
  $.get("http://localhost:8000/?q="+query, function(data) {
      //if(data.isOk == false)
        result= eval('('+data+')');
        func(result);
  });          
}



