$(document).ready(function() {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(function(stream) {
            var video = document.querySelector('video');
            video.srcObject = stream;
            setInterval(function() {
                captureAndRecognize(video);
            }, 1000);
        })
        .catch(function(err) {
            console.error('Error accessing camera: ', err);
        });

    function captureAndRecognize(video) {
        var canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        var context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        var imageData = canvas.toDataURL('image/jpeg');
        $.ajax({
            url: '{% url "face_recognition" %}',
            method: 'POST',
            data: { image_data: imageData },
            success: function(response) {
            },
            error: function(xhr, status, error) {
                console.error('Error sending image for recognition: ', error);
            }
        });
    }
});
