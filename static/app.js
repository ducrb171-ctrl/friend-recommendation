const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
let currentUser = null;

// Hàm API hỗ trợ FormData
async function api(path, options = {}) {
    const opts = { ...options };
    if (opts.body && !(opts.body instanceof FormData)) {
        opts.headers = { ...opts.headers, "Content-Type": "application/json" };
        opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Lỗi: ${res.status}`);
    return data;
}

function getAvatar(url, name) {
    if (!url) return `https://ui-avatars.com/api/?name=${name || 'U'}&background=random`;
    // Nếu là link web ngoài hoặc đã có sẵn đường dẫn tĩnh thì giữ nguyên
    if (url.startsWith('http') || url.startsWith('/')) return url;
    // Nếu chỉ có tên file (ảnh mới upload) thì gắn thư mục uploads vào
    return `/static/uploads/${url}`;
}
function timeAgo(dateString) {
    if (!dateString) return "Vừa xong";
    const seconds = Math.floor((new Date() - new Date(dateString)) / 1000);
    if (seconds < 60) return "Vừa xong";

    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) return interval + " năm trước";
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) return interval + " tháng trước";
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) return interval + " ngày trước";
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) return interval + " giờ trước";
    interval = Math.floor(seconds / 60);
    return interval + " phút trước";
}

// RENDER BÀI VIẾT (FEED)
function renderPost(post) {
    const imgHtml = post.image ? `<img src="/static/uploads/${post.image}" class="post-image">` : "";
    const likeClass = post.isLikedByMe ? "liked" : "";
    const likeIcon = post.isLikedByMe ? "bxs-heart" : "bx-heart";
    const delBtn = post.authorId === currentUser?.id ? `<button class="action-btn" data-action="delete-post" data-id="${post.id}"><i class='bx bx-trash'></i></button>` : "";

    return `
    <div class="post-item card">
        <div class="post-header">
            <img class="avatar" src="${getAvatar(post.authorAvatar, post.authorName)}" style="cursor:pointer" onclick="loadProfile('${post.authorUsername}')">
            <div><b style="cursor:pointer" onclick="loadProfile('${post.authorUsername}')">${post.authorName}</b> <small class="text-muted">· ${timeAgo(post.createdAt)}</small></div>
        </div>
        <div class="post-content">
            <p>${post.content}</p>
            ${imgHtml}
        </div>
        <div class="post-footer">
            <button class="action-btn ${likeClass}" data-action="${post.isLikedByMe ? 'unlike-post' : 'like-post'}" data-id="${post.id}">
                <i class='bx ${likeIcon}'></i> ${post.likes || 0}
            </button>
            <button class="action-btn" data-action="toggle-comments" data-id="${post.id}">
                <i class='bx bx-message-rounded'></i> Bình luận
            </button>
            ${delBtn}
        </div>
        <!-- Vùng chứa bình luận (Mặc định ẩn) -->
        <div class="comments-section hidden" id="comments-section-${post.id}">
            <div id="comments-list-${post.id}"></div>
            <div class="comment-input-area">
                <img class="avatar" style="width:32px;height:32px" src="${getAvatar(currentUser?.avatar, currentUser?.name)}">
                <input type="text" id="comment-input-${post.id}" placeholder="Viết bình luận..." onkeypress="if(event.key === 'Enter') document.getElementById('btn-send-cmt-${post.id}').click()">
                <button class="btn-primary" style="padding: 8px 15px" id="btn-send-cmt-${post.id}" data-action="submit-comment" data-id="${post.id}">Gửi</button>
            </div>
        </div>
    </div>`;
}

// RENDER NGƯỜI DÙNG (WIDGET / LIST)
function renderPerson(p, mode) {
    let btn = "";
    if (mode === "discover") btn = `<div class="widget-actions"><button data-action="add-friend" data-id="${p.id}" class="btn-primary">Kết bạn</button><button data-action="follow" data-id="${p.id}" class="btn-secondary">Theo dõi</button></div>`;
    if (mode === "friends") btn = `<button data-action="unfriend" data-id="${p.id}" class="btn-secondary text-danger">Hủy bạn</button>`;
    if (mode === "requests") btn = `<button data-action="accept-req" data-id="${p.senderId}" class="btn-primary">Chấp nhận</button>`;
    if (mode === "following") btn = `<button data-action="unfollow" data-id="${p.id}" class="btn-secondary text-primary">Đang theo dõi</button>`;
    if (mode === "followers") btn = `<button data-action="follow" data-id="${p.id}" class="btn-secondary">Theo dõi lại</button>`;

    return `<div class="${mode === 'discover' ? 'widget-item' : 'person-card'}">
                <img class="avatar" src="${getAvatar(p.avatar, p.name)}" style="cursor:pointer" onclick="loadProfile('${p.username}')">
                <div class="widget-item-info">
                    <b style="cursor:pointer" onclick="loadProfile('${p.username}')">${p.name}</b><br>
                    <small class="text-muted">${p.mutualFriendsCount ? p.mutualFriendsCount + ' bạn chung' : ''}</small>
                </div>
                ${btn}
            </div>`;
}

// VIEW CONTROLLER
function switchView(viewName) {
    $$(".view").forEach(el => el.classList.add("hidden"));
    $(`#view-${viewName}`)?.classList.remove("hidden");
    $$(".nav-menu button").forEach(b => b.classList.toggle("active", b.dataset.view === viewName));

    const titles = { home: "Bảng tin", friends: "Bạn bè", requests: "Lời mời", profile: "Hồ sơ cá nhân" };
    if (titles[viewName]) {
        $("#page-title").textContent = titles[viewName];
        $("#post-form")?.closest(".card")?.classList.remove("hidden"); // Hiện lại form đăng bài nếu đang ở home
    }

    if (viewName === "home") loadFeed();
    if (viewName === "friends") loadFriends();
    if (viewName === "requests") loadRequests();
    if (viewName === "profile" && currentUser) {
        $("#prof-name").value = currentUser.name || "";
        $("#prof-bio").value = currentUser.bio || "";
        $("#prof-display-name").textContent = currentUser.name;
        $("#prof-display-bio").textContent = currentUser.bio || "Chưa có tiểu sử";
        $("#prof-display-avatar").src = getAvatar(currentUser.avatar, currentUser.name);
        loadUserPosts(currentUser.id, "#my-posts-list");
    }
}

// DATA LOADERS
async function loadUserData() {
    currentUser = await api("/api/me");
    $("#side-name").textContent = currentUser.name;
    const avt = getAvatar(currentUser.avatar, currentUser.name);
    $("#nav-avatar").src = avt;
    $("#composer-avatar").src = avt;
}

async function loadFeed() {
    const data = await api("/api/feed");
    $("#feed-list").innerHTML = data.length ? data.map(renderPost).join("") : `<div class="empty-state">Chưa có bài viết nào.</div>`;
}

async function loadComments(postId) {
    const data = await api(`/api/posts/${postId}/comments`);
    const container = $(`#comments-list-${postId}`);
    container.innerHTML = data.length ? data.map(c => `
        <div class="comment-item">
            <img class="avatar" src="${getAvatar(c.authorAvatar, c.authorName)}" style="cursor:pointer" onclick="loadProfile('${c.authorUsername}')">
            <div>
                <div class="comment-bubble"><b>${c.authorName}</b> ${c.content}</div>
                <div class="comment-meta">${timeAgo(c.createdAt)}</div>
            </div>
        </div>
    `).join("") : `<div class="text-muted" style="font-size: 13px; text-align: center; margin-bottom: 10px;">Hãy là người đầu tiên bình luận.</div>`;
}

async function loadUserPosts(userId, containerSelector) {
    const data = await api(`/api/users/${userId}/posts`);
    $(containerSelector).innerHTML = data.length ? data.map(renderPost).join("") : `<div class="empty-state">Chưa có bài viết nào.</div>`;
}

// HÀM TẢI PROFILE CỦA NGƯỜI KHÁC KHI TÌM KIẾM HOẶC CLICK
// HÀM TẢI PROFILE CHUẨN (Không bị Bảng tin ghi đè)
async function loadProfile(username) {
    try {
        const profile = await api(`/api/users/${username}`);

        // 1. Tự hiển thị View Home nhưng KHÔNG dùng switchView() để chặn loadFeed()
        $$(".view").forEach(el => el.classList.add("hidden"));
        $("#view-home")?.classList.remove("hidden");

        // 2. Ẩn form đăng bài và Đổi tiêu đề
        $("#post-form")?.closest(".card")?.classList.add("hidden");
        $("#page-title").textContent = `Hồ sơ của ${profile.name}`;

        // 3. Xử lý logic Nút bấm (Kết bạn, Hủy lời mời, Theo dõi...)
        let buttonsHtml = '';
        if (currentUser && profile.username !== currentUser.username) {

            // Nhóm Kết bạn
            if (profile.isFriend) {
                buttonsHtml += `<button data-action="unfriend" data-id="${profile.id}" class="btn-secondary text-danger">Hủy kết bạn</button>`;
            } else if (profile.sentRequest) {
                buttonsHtml += `<button data-action="cancel-req" data-id="${profile.id}" class="btn-secondary">Hủy lời mời</button>`;
            } else if (profile.receivedRequest) {
                buttonsHtml += `<button data-action="accept-req" data-id="${profile.id}" class="btn-primary">Chấp nhận kết bạn</button>`;
            } else {
                buttonsHtml += `<button data-action="add-friend" data-id="${profile.id}" class="btn-primary">Thêm bạn bè</button>`;
            }

            // Nhóm Theo dõi
            if (profile.isFollowing) {
                buttonsHtml += `<button data-action="unfollow" data-id="${profile.id}" class="btn-secondary text-primary">Đang theo dõi</button>`;
            } else {
                buttonsHtml += `<button data-action="follow" data-id="${profile.id}" class="btn-secondary">Theo dõi</button>`;
            }
        }

        const avatarUrl = getAvatar(profile.avatar, profile.name);

        // 4. Vẽ Card Hồ sơ trực tiếp đè lên khung Bảng tin
        $("#feed-list").innerHTML = `
            <div class="profile-header-container card" style="padding: 20px; text-align: center; margin-bottom: 20px;">
                <img src="${avatarUrl}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; margin-bottom: 15px; border: 3px solid var(--primary-color);">
                <h2 style="margin: 0; font-size: 22px;">${profile.name}</h2>
                <p class="text-muted" style="margin-bottom: 10px;">@${profile.username}</p>
                <p style="margin-top: 10px; font-size: 15px;">${profile.bio || 'Người dùng này chưa có tiểu sử.'}</p>
                
                <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: center;">
                    ${buttonsHtml}
                </div>
            </div>
            
            <!-- Khu vực chứa bài viết của riêng người này -->
            <div id="user-specific-posts" class="empty-state">
                <i class='bx bx-loader-alt bx-spin' ></i> Đang tải bài viết...
            </div>
        `;

        // 5. Tải bài viết riêng của người này nhét vào khung bên dưới
        loadUserPosts(profile.id, "#user-specific-posts");

    } catch (err) {
        console.error(err);
        alert('Không thể tải trang cá nhân');
    }
}

async function loadRecommendations() {
    const data = await api(`/api/recommendations?hops=${$("#hops-select").value}`);
    $("#recommendations-list").innerHTML = data.length ? data.map(p => renderPerson(p, "discover")).join("") : `<div class="empty-state">Không có gợi ý.</div>`;
}

async function loadFriends() {
    const data = await api("/api/friends");
    $("#friends-list").innerHTML = data.length ? data.map(p => renderPerson(p, "friends")).join("") : `<div class="empty-state">Chưa có bạn bè.</div>`;
}
async function loadFollowing() {
    const data = await api("/api/following");
    $("#following-list").innerHTML = data.length ? data.map(p => renderPerson(p, "following")).join("") : `<div class="empty-state">Bạn chưa theo dõi ai.</div>`;
}
async function loadFollowers() {
    const data = await api("/api/followers");
    $("#followers-list").innerHTML = data.length ? data.map(p => renderPerson(p, "followers")).join("") : `<div class="empty-state">Chưa có ai theo dõi bạn.</div>`;
}
async function loadRequests() {
    const data = await api("/api/friend-requests");
    const badge = $("#req-badge");
    if (data.length > 0) { badge.textContent = data.length; badge.classList.remove("hidden"); } else { badge.classList.add("hidden"); }
    $("#requests-list").innerHTML = data.length ? data.map(p => renderPerson(p, "requests")).join("") : `<div class="empty-state">Không có lời mời.</div>`;
}

// SỰ KIỆN CLICK CHUNG
document.addEventListener("click", async (e) => {
    if (e.target.closest("[data-view]")) { switchView(e.target.closest("[data-view]").dataset.view); return; }

    // Đổi tab trong Profile
    if (e.target.classList.contains("tab-btn")) {
        const tabName = e.target.dataset.tab;
        $$(".tab-btn").forEach(b => b.classList.remove("active"));
        e.target.classList.add("active");
        $$(".tab-content").forEach(c => c.classList.add("hidden"));
        $(`#profile-tab-${tabName}`).classList.remove("hidden");

        if (tabName === 'following') loadFollowing();
        if (tabName === 'followers') loadFollowers();
        return;
    }

    const btn = e.target.closest("[data-action]"); if (!btn) return;
    const id = btn.dataset.id, act = btn.dataset.action;

    try {
        if (act === "add-friend") {
            await api("/api/friend-requests", { method: "POST", body: { receiverId: id } });
            btn.dataset.action = "cancel-req"; btn.className = "btn-secondary"; btn.textContent = "Đã gửi lời mời";
        }
        else if (act === "cancel-req") {
            await api(`/api/friend-requests/${id}`, { method: "DELETE" });
            btn.dataset.action = "add-friend"; btn.className = "btn-primary"; btn.textContent = "Thêm bạn bè";
        }
        else if (act === "follow") {
            await api(`/api/follow/${id}`, { method: "POST" });
            btn.dataset.action = "unfollow"; btn.className = "btn-secondary text-primary"; btn.textContent = "Đang theo dõi";
        }
        else if (act === "unfollow") {
            await api(`/api/follow/${id}`, { method: "DELETE" });
            btn.dataset.action = "follow"; btn.className = "btn-secondary"; btn.textContent = "Theo dõi";
        }
        else if (act === "unfriend") {
            if (confirm("Hủy kết bạn?")) {
                await api(`/api/friends/${id}`, { method: "DELETE" });
                // Xử lý reload view tùy vị trí đứng
                if ($("#view-friends").classList.contains("hidden") === false) loadFriends();
                else btn.textContent = "Đã hủy bạn";
            }
        }
        else if (act === "accept-req") {
            await api(`/api/friend-requests/${id}/accept`, { method: "POST" });
            loadRequests();
            btn.textContent = "Đã chấp nhận"; btn.disabled = true;
        }
        else if (act === "like-post") { await api(`/api/posts/${id}/like`, { method: "POST" }); loadFeed(); if (currentUser) loadUserPosts(currentUser.id, "#my-posts-list"); }
        else if (act === "unlike-post") { await api(`/api/posts/${id}/like`, { method: "DELETE" }); loadFeed(); if (currentUser) loadUserPosts(currentUser.id, "#my-posts-list"); }
        else if (act === "delete-post") { if (confirm("Xóa bài viết này?")) { await api(`/api/posts/${id}`, { method: "DELETE" }); loadFeed(); if (currentUser) loadUserPosts(currentUser.id, "#my-posts-list"); } }
        else if (act === "toggle-comments") {
            const section = $(`#comments-section-${id}`);
            section.classList.toggle("hidden");
            if (!section.classList.contains("hidden")) loadComments(id);
        }
        else if (act === "submit-comment") {
            const input = $(`#comment-input-${id}`);
            if (!input.value.trim()) return;

            await api(`/api/posts/${id}/comments`, {
                method: "POST",
                body: { content: input.value.trim() }
            });

            input.value = "";
            loadComments(id);
        }
    } catch (err) { alert(err.message); }
});

$("#toggle-sidebar-right")?.addEventListener("click", () => {
    $("#sidebar-right").classList.toggle("collapsed");
});

// FORM SUBMITS (Hỗ trợ File)
$("#post-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("content", $("#post-content").value);
    if ($("#post-image").files[0]) formData.append("image", $("#post-image").files[0]);

    const btn = $("#btn-post"); btn.disabled = true; btn.textContent = "...";
    try {
        await api("/api/posts", { method: "POST", body: formData });
        $("#post-form").reset();
        $("#post-preview-img").classList.add("hidden");
        loadFeed();
    } catch (err) { alert(err.message); }
    btn.disabled = false; btn.textContent = "Đăng";
});

// Preview ảnh khi chọn đăng bài
$("#post-image").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
        const url = URL.createObjectURL(file);
        $("#post-preview-img").src = url;
        $("#post-preview-img").classList.remove("hidden");
    }
});

$("#profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("name", $("#prof-name").value);
    formData.append("bio", $("#prof-bio").value);
    if ($("#prof-avatar-file").files[0]) formData.append("avatar", $("#prof-avatar-file").files[0]);

    try {
        await api("/api/me", { method: "PATCH", body: formData });
        alert("Lưu hồ sơ thành công!");
        await loadUserData();
        switchView("profile");
    } catch (err) { alert(err.message); }
});

$("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
        await api("/api/login", { method: "POST", body: { username: $("#login-username").value, password: $("#login-password").value } });
        await refreshApp();
    } catch (err) { $("#login-error").textContent = err.message; }
});

// Chuyển đổi qua lại giữa Đăng nhập và Đăng ký
$("#show-login")?.addEventListener("click", () => {
    $("#show-login").classList.add("active");
    $("#show-register").classList.remove("active");
    $("#login-form").classList.remove("hidden");
    $("#register-form").classList.add("hidden");
    $("#register-error").textContent = "";
});

$("#show-register")?.addEventListener("click", () => {
    $("#show-register").classList.add("active");
    $("#show-login").classList.remove("active");
    $("#register-form").classList.remove("hidden");
    $("#login-form").classList.add("hidden");
    $("#login-error").textContent = "";
});

// Xử lý gửi Form Đăng ký
$("#register-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button");
    const errorMsg = $("#register-error");
    errorMsg.textContent = "";
    btn.disabled = true;
    btn.textContent = "Đang xử lý...";

    try {
        const res = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: $("#reg-name").value.trim(),
                username: $("#reg-username").value.trim(),
                password: $("#reg-password").value
            })
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || "Đăng ký thất bại");

        alert("Đăng ký thành công! Hãy đăng nhập nhé.");
        $("#show-login").click();
        $("#login-username").value = $("#reg-username").value;
        e.target.reset();
    } catch (err) {
        errorMsg.textContent = err.message;
    } finally {
        btn.disabled = false;
        btn.textContent = "Tạo tài khoản";
    }
});

$("#logout-btn").addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" });
    currentUser = null;
    $("#dashboard").classList.add("hidden");
    $("#login-panel").classList.remove("hidden");
});

$("#refresh-btn").addEventListener("click", () => switchView($(".nav-menu button.active").dataset.view));
$("#hops-select").addEventListener("change", loadRecommendations);

async function refreshApp() {
    try {
        await loadUserData();
        $("#login-panel").classList.add("hidden");
        $("#dashboard").classList.remove("hidden");
        loadRequests();
        loadRecommendations();
        switchView("home");
    } catch (e) { }
}

// Tính năng Thu gọn/Mở rộng Sidebar
$("#toggle-sidebar").addEventListener("click", () => {
    $("#sidebar").classList.toggle("collapsed");
});

// Xử lý nút thêm Emoji vào ô nhập bài viết
$("#emoji-btn")?.addEventListener("click", () => {
    const el = $("#post-content");
    if (el) {
        el.value += "😊";
        el.focus();
    }
});

// Tính năng Tìm kiếm người dùng
const searchInput = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');

if (searchInput) {
    searchInput.addEventListener('input', async (e) => {
        const term = e.target.value.trim();

        if (term.length === 0) {
            searchResults.innerHTML = '';
            searchResults.classList.add('hidden');
            return;
        }

        try {
            const users = await api(`/api/users/search?q=${encodeURIComponent(term)}`);
            searchResults.innerHTML = '';

            if (users.length === 0) {
                searchResults.innerHTML = '<div style="padding: 10px; text-align: center; color: #666;">Không tìm thấy</div>';
            } else {
                users.forEach(user => {
                    const div = document.createElement('div');
                    div.className = 'search-result-item';

                    const avatarUrl = getAvatar(user.avatar, user.name);

                    div.innerHTML = `
                        <img src="${avatarUrl}" alt="avatar">
                        <div>
                            <strong>${user.name}</strong><br>
                            <small style="color: #666;">@${user.username}</small>
                        </div>
                    `;

                    div.onclick = () => {
                        loadProfile(user.username);
                        searchResults.classList.add('hidden');
                        searchInput.value = '';
                    };

                    searchResults.appendChild(div);
                });
            }
            searchResults.classList.remove('hidden');
        } catch (err) {
            console.error('Lỗi tìm kiếm:', err);
        }
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add('hidden');
        }
    });
}

// Khởi chạy app ban đầu
refreshApp();