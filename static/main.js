function wordCount( val ){
    var wom = val.match(/\S+/g);
    return {
        charactersNoSpaces : val.replace(/\s+/g, '').length,
        characters         : val.length,
        words              : wom ? wom.length : 0,
        lines              : val.split(/\r*\n/).length
    };
}


var textarea = document.getElementById("text");
var result   = document.getElementById("result");

textarea.addEventListener("input", function(){
  var v = wordCount( this.value );
  result.innerHTML = (
      "<br>Characters (no spaces):  "+ v.charactersNoSpaces +
      "<br>Characters (and spaces): "+ v.characters +
      "<br>Words: "+ v.words +
      "<br>Lines: "+ v.lines
  );
}, false);