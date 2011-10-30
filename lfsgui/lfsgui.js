window.onload = function (){
  set({name:'DIV#main'});
  
  set({name:'DIV#labeltree', parent:'DIV#main'});
    set({name:'SPAN#fooo', parent:'DIV#labeltree'});
    set({name:'SPAN#foo', text:'labeltree', parent:'SPAN#fooo'});

  set({name:'DIV#queryresults', parent:'DIV#main'});
    set({name:'DIV#locationbar', parent:'DIV#queryresults'});
      set({name:'SPAN#fooo2', parent:'DIV#locationbar'});
      set({name:'SPAN#foo2', text:'locationbar', parent:'SPAN#fooo2'});
    set({name:'DIV#filegrid', parent:'DIV#queryresults'});
    
  set({name:'DIV#filedetails', parent:'DIV#main'});
    set({name:'SPAN#fooo3', parent:'DIV#filedetails'});
    set({name:'SPAN#foo3', text:'filedetails', parent:'SPAN#fooo3'});

  
  lfsquery('~"*"', function(result){
    var i=0;
    for(node in result){
      name = result[node]['name']
      set({name:'DIV#'+name, attrs:{class:'gridfile'}, parent:'DIV#filegrid'});
      //set({name:'P#'+name, parent:'DIV#'+name});
      set({name:'SPAN#'+i+name, text:name, parent:'DIV#'+name});
      i++;
    }
  });
}
