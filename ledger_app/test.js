const readline = require('readline'); 
const rl = readline.createInterface({ input: process.stdin, output: process.stdout }); 

rl.question('Enter a number: ', (answer) => { 
  const a = parseInt(answer); 
  console.log(a); 
  rl.close(); 
});