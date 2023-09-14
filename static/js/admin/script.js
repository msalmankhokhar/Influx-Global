let nav = document.getElementById('nav');
let menuBtn = document.getElementById('menuBtn');
let main = document.getElementById('main');

let dropdownBtnList = document.querySelectorAll('.dropdownBtn');

let open = false;

menuBtn.addEventListener('click', (e=>{
    main.classList.toggle('faded');
    nav.classList.toggle('open');
    open = !open;
}))

// menuBtn.addEventListener('blur', (e=>{
//     if (open){       
//         main.classList.remove('faded');
//         nav.classList.remove('open');
//         open = false;
//     }
// }))

dropdownBtnList.forEach(dropdownBtn => {
    dropdownBtn.addEventListener('click', (e)=>{
        let content = e.target.nextElementSibling;
        let navlinkList =  Array.from(content.children);
        // console.log(navlinkList);
        content.classList.toggle('dropdownClose');
        navlinkList.forEach(navlink => {
            navlink.classList.toggle('dropdownClose');
            console.log(navlink);
        });

        // setTimeout(() => {
        //     content.classList.toggle('displayNone');
        //     navlinkList.forEach(navlink => {
        //         navlink.classList.toggle('displayNone');
        //         console.log(navlink);
        //     });
        // }, 400);

    })
});

