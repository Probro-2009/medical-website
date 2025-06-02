// Simple local video preview
const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");

navigator.mediaDevices.getUserMedia({ video: true, audio: true })
  .then(stream => {
    localVideo.srcObject = stream;
    // NOTE: WebRTC peer connection logic should go here
    console.log("Local stream started.");
  })
  .catch(err => {
    console.error("Error accessing media devices.", err);
  });
