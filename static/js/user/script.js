let logoutBtnList = document.querySelectorAll('.logoutBtn');

logoutBtnList.forEach(logoutBtn => {
    logoutBtn.addEventListener('click', (e)=>{
        e.preventDefault();
        user_confirmation = window.confirm("Are you sure to Log Out?");
        if (user_confirmation){
            window.location.href = logoutBtn.href;
            // console.log(logoutBtn)
        }
    })
});