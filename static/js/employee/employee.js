function InfoItem({ label, value }) {
    return `
        <div class="group">
            <label class="text-sm text-[#b3b3b3] group-hover:text-[#2196F3] transition-colors">${label}</label>
            <p class="font-medium text-white mt-1">${value}</p>
        </div>
    `;
}