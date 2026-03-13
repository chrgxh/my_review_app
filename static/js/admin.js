document
  .getElementById("reviewRequestForm")
  .addEventListener("submit", function (e) {

    e.preventDefault()

    const email = document.getElementById("recipientEmail").value
    const identifier = document.getElementById("identifier").value
    const message = document.getElementById("message").value

    console.log("email:", email)
    console.log("identifier:", identifier)
    console.log("message:", message)

})