const socket = io();
const room = room_id;
const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');
let localStream;
let peerConnection;
const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

// Join room
socket.emit('join', room);

document.addEventListener("DOMContentLoaded", function () {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720 },
            audio: { echoCancellation: true, noiseSuppression: true }
        }).then(stream => {
            localStream = stream;
            const localVideo = document.getElementById("localVideo");
            localVideo.srcObject = stream;
            console.log("✅ Local media stream started.");
        }).catch(err => {
            console.error("❌ Media device error:", err.name, err.message);
        });
    } else {
        console.error("❌ navigator.mediaDevices.getUserMedia not supported in this browser.");
    }
});



// Signaling handlers
socket.on('joined', () => {
    if (!peerConnection) startPeer(true);
});

socket.on('offer', offer => {
    startPeer(false);
    peerConnection.setRemoteDescription(new RTCSessionDescription(offer)).then(() =>
        peerConnection.createAnswer()
    ).then(answer => {
        peerConnection.setLocalDescription(answer);
        socket.emit('answer', room, answer);
    });
});

socket.on('answer', answer => {
    peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
});

socket.on('ice-candidate', candidate => {
    peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
});

function startPeer(initiator) {
    peerConnection = new RTCPeerConnection(config);
    peerConnection.onicecandidate = e => {
        if (e.candidate) socket.emit('ice-candidate', room, e.candidate);
    };
    peerConnection.ontrack = e => remoteVideo.srcObject = e.streams[0];
    localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

    if (initiator) {
        peerConnection.createOffer().then(offer => {
            peerConnection.setLocalDescription(offer);
            socket.emit('offer', room, offer);
        });
    }
}
navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(stream => {
    localStream = stream;
    localVideo.srcObject = stream;
    console.log("✅ Local media stream set.");
}).catch(err => {
    console.error("❌ Error accessing media devices:", err);
});
