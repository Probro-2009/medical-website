# video.py
from flask import Blueprint, render_template, request

video = Blueprint(
    'video', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/video'
)

@video.route('/call/<room_id>')
def video_call(room_id):
    return render_template('video_call.html', room_id=room_id, full_url=request.url)