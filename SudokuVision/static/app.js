"use strict";
const $ = (id) => document.getElementById(id);
let selectedFile = null, objectURL = null, busy = false, solved = false, given = null;
const cells = [];
const empty = () => Array.from({length: 9}, () => Array(9).fill(0));
function message(text, kind = "neutral") { $("status").textContent = text; $("status").className = "status " + kind; }
function values() { return Array.from({length:9}, (_,r) => cells.slice(r*9,r*9+9).map(el => Number(el.value) || 0)); }
function controls() {
  $("solve").disabled = busy || solved || !cells.some(el => el.value);
  $("read").disabled = busy || !selectedFile; $("image").disabled = busy; $("manual").disabled = busy;
  $("reset").disabled = busy;
  document.querySelectorAll(".example").forEach(el => el.disabled = busy);
  cells.forEach(el => el.readOnly = busy || solved);
  $("clue-count").textContent = (given && solved ? given.flat().filter(Boolean).length : cells.filter(el => el.value).length) + " pistas";
}
function mark(list, className) { list.forEach(([r,c]) => cells[r*9+c].classList.add(className)); }
function showBoard(board) {
  cells.forEach((el,i) => {
    el.value = board[Math.floor(i/9)][i%9] || "";
    el.classList.remove("doubtful","conflict","calculated");
  });
  solved = false; given = null; $("edit").hidden = true;
  controls();
}
for (let r=0;r<9;r++) for (let c=0;c<9;c++) {
  const el = document.createElement("input"); el.type = "text"; el.inputMode = "numeric"; el.maxLength=1;
  el.autocomplete="off"; el.setAttribute("aria-label", "Fila " + (r+1) + ", columna " + (c+1));
  el.className = "cell" + ([2,5].includes(c) ? " right-block" : "") + ([2,5].includes(r) ? " bottom-block" : "");
  el.addEventListener("input", () => {
    el.value=el.value.replace(/[^1-9]/g,""); el.classList.remove("doubtful");
    cells.forEach(cell => cell.classList.remove("conflict")); controls();
  });
  el.addEventListener("keydown", e => {
    const move={ArrowRight:1,ArrowLeft:-1,ArrowDown:9,ArrowUp:-9}[e.key];
    if (move) { e.preventDefault(); cells[Math.max(0,Math.min(80,r*9+c+move))].focus(); }
    if (!el.readOnly && ["Delete","Backspace"].includes(e.key)) { el.value=""; el.dispatchEvent(new Event("input")); }
  });
  el.addEventListener("focus",()=>el.select()); cells.push(el); $("board").append(el);
}
function selectFile(file) {
  if (!file) return;
  selectedFile=null; controls();
  if (file.size>8*1024*1024) { message("La imagen supera los 8 MB.", "error"); return; }
  if (!["image/png","image/jpeg"].includes(file.type)) { message("Selecciona una imagen PNG o JPG.", "error"); return; }
  selectedFile=file; if(objectURL) URL.revokeObjectURL(objectURL);
  objectURL=URL.createObjectURL(file); $("preview").src=objectURL; $("preview-wrap").hidden=false;
  $("filename").textContent=file.name; showBoard(empty());
  message("Imagen preparada. Pulsa «Detectar números» para leer el tablero."); controls();
}
$("image").addEventListener("change",e=>selectFile(e.target.files[0]));
["dragenter","dragover"].forEach(type=>$("dropzone").addEventListener(type,e=>{e.preventDefault();if(!busy)$("dropzone").classList.add("drag");}));
["dragleave","drop"].forEach(type=>$("dropzone").addEventListener(type,e=>{e.preventDefault();$("dropzone").classList.remove("drag");}));
$("dropzone").addEventListener("drop",e=>{if(!busy)selectFile(e.dataTransfer.files[0]);});
async function api(path, options) {
  const response=await fetch(path, {...options, headers:{"X-Sudoku-Request":"1",...(options.headers||{})}});
  let result; try {result=await response.json();} catch {throw new Error("El servidor no responde correctamente. Inténtalo de nuevo.");}
  if(!response.ok) throw new Error(result.message || "No se ha podido completar la operación.");
  return result;
}
async function read() {
  if(!selectedFile || busy)return;
  busy=true; controls(); message("Leyendo la cuadrícula y comprobando la orientación… La primera lectura puede tardar unos segundos.","busy");
  try{
    const form=new FormData();form.append("image",selectedFile);
    const result=await api("/api/read",{method:"POST",body:form});
    showBoard(result.board);mark(result.uncertain,"doubtful");mark(result.conflicts,"conflict");
    $("preview").src=result.preview;
    $("filename").textContent=result.rotation ? "Tablero enderezado y girado " + result.rotation + "° para su revisión." : "Tablero detectado. Compáralo con las pistas de la derecha.";
    const count=result.uncertain.length;
    message(result.message+(count ? " Hay " + count + " casillas dudosas." : "")+(result.conflicts.length ? " Hay cifras repetidas marcadas en rojo." : ""));
  }catch(e){showBoard(empty());message(e.message,"error");}
  finally{busy=false;controls();}
}
$("read").addEventListener("click",read);
document.querySelectorAll(".example").forEach(btn=>btn.addEventListener("click",async()=>{
  if(busy)return; busy=true;controls(); let loaded=false;
  try{const r=await fetch("/static/examples/sudoku-"+btn.dataset.example+".png");if(!r.ok)throw new Error("No se puede cargar el ejemplo.");
    selectFile(new File([await r.blob()],"ejemplo-"+btn.dataset.example+".png",{type:"image/png"}));
    loaded=true;
  }catch(e){message(e.message,"error");}
  finally{busy=false;controls();}
  if(loaded)await read();
}));
$("solve").addEventListener("click",async()=>{
  if(busy)return;
  const board=values();busy=true;controls();message("Comprobando las pistas y la unicidad de la solución…","busy");
  try{
    const result=await api("/api/solve",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({board})});
    cells.forEach(el=>el.classList.remove("conflict"));
    if(result.status==="solved"){showBoard(result.solution);given=board;solved=true;
      cells.forEach((el,i)=>{if(!board[Math.floor(i/9)][i%9])el.classList.add("calculated");});
      $("edit").hidden=false;message(result.message,"success");
    }else{mark(result.conflicts||[],"conflict");message(result.message,"error");}
  }catch(e){message(e.message,"error");}
  finally{busy=false;controls();}
});
$("edit").addEventListener("click",()=>{showBoard(given);message("Puedes corregir las pistas y volver a resolver.");});
$("manual").addEventListener("click",()=>{selectedFile=null;$("image").value="";showBoard(empty());$("preview-wrap").hidden=true;message("Introduce las pistas originales. Deja vacías las casillas sin número.");cells[0].focus();});
$("reset").addEventListener("click",()=>{
  showBoard(empty());selectedFile=null;$("image").value="";$("preview-wrap").hidden=true;
  if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}
  message("Empieza con una imagen o introduce las pistas a mano.");controls();
});
controls();
