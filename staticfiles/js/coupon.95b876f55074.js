function createNewCoupon() {
    // Show modal/form for creating new coupon
    window.location.href = "/masteradmin/create_coupon/";
}
function deleteCoupon(couponId) {
    if (confirm('Are you sure you want to delete this coupon?')) {
        fetch('/masteradmin/delete_coupon/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                'coupon_id': couponId
            })
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                alert('Error deleting coupon');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting coupon');
        });
    }
}