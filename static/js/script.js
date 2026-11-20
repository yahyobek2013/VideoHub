function readCookie(name) {
	const cookie = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${name}=`));
	return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
}

const splash = document.querySelector("[data-splash]");
if (splash) {
	window.setTimeout(() => window.location.replace(splash.dataset.redirectUrl), 3000);
}

document.addEventListener("click", (event) => {
	const openLogout = event.target.closest("[data-open-logout]");
	if (openLogout) {
		document.querySelector("#logout-confirm")?.showModal();
		return;
	}
	const closeLogout = event.target.closest("[data-close-logout]");
	if (closeLogout) {
		document.querySelector("#logout-confirm")?.close();
		return;
	}
	const backLink = event.target.closest("[data-history-back]");
	if (backLink && window.history.length > 1) {
		event.preventDefault();
		window.history.back();
	}
});

function syncInteractionState(button, data) {
	if (button.dataset.action === "like") {
		button.classList.toggle("is-liked", data.liked);
		button.setAttribute("aria-pressed", String(data.liked));
		const count = button.querySelector("[data-like-count]");
		if (count) count.textContent = data.like_count;
	}
	if (button.dataset.action === "save") {
		button.classList.toggle("is-saved", data.saved);
		button.setAttribute("aria-pressed", String(data.saved));
		button.setAttribute("aria-label", data.saved ? "Saqlanganlardan olib tashlash" : "Saqlanganlarga qo‘shish");
		const label = button.querySelector("[data-saved-label]");
		if (label) label.textContent = data.saved ? "Saqlangan" : "Saqlash";
	}
	if (button.dataset.action === "reaction") {
		document.querySelectorAll('[data-action="reaction"]').forEach((reactionButton) => {
			const selected = reactionButton.dataset.kind === data.reaction;
			reactionButton.classList.toggle("is-selected", selected);
			reactionButton.setAttribute("aria-pressed", String(selected));
		});
	}
	document.querySelectorAll("[data-reaction-count]").forEach((count) => {
		count.textContent = data.reaction_counts[count.dataset.reactionCount] ?? 0;
	});
	document.querySelectorAll("[data-reaction-total]").forEach((total) => {
		total.textContent = data.reaction_total;
	});
}

document.addEventListener("click", async (event) => {
	const closeButton = event.target.closest(".message-close");
	if (closeButton) {
		closeButton.closest(".message")?.remove();
		return;
	}

	const button = event.target.closest("[data-action]");
	if (!button || button.disabled) return;

	const formData = new FormData();
	if (button.dataset.kind) formData.set("kind", button.dataset.kind);
	button.disabled = true;
	try {
		const response = await fetch(button.dataset.url, {
			method: "POST",
			credentials: "same-origin",
			headers: { "X-CSRFToken": readCookie("csrftoken"), "X-Requested-With": "XMLHttpRequest" },
			body: formData,
		});
		const data = await response.json();
		if (!response.ok || !data.ok) throw new Error(data.error || "So‘rov bajarilmadi.");
		syncInteractionState(button, data);
	} catch (error) {
		window.alert(error.message || "Ulanishda xatolik yuz berdi.");
	} finally {
		button.disabled = false;
	}
});

document.addEventListener("submit", (event) => {
	const form = event.target.closest("form[data-confirm]");
	if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
});
