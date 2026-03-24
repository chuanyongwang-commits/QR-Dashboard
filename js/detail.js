const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        const item = ref(null);
        const selectedTab = ref(1);
        const isModalActive = ref(false);
        const isEditMode = ref(false); 

        onMounted(() => {
            loadDetail();
        });

        function loadDetail() {
            const urlParams = new URLSearchParams(window.location.search);
            const qrId = urlParams.get('id');

            if (qrId) {
                fetch(`/api/cases/${qrId}`)
                    .then(r => {
                         if (!r.ok) throw new Error('Not found');
                         return r.json();
                    })
                    .then(data => {
                         data.ep_directions = [
                              { reliability: data.ep1_reliability, cost: data.ep1_cost, applicability: data.ep1_applicability, races: data.ep1_races },
                              { reliability: data.ep2_reliability, cost: data.ep2_cost, applicability: data.ep2_applicability, races: data.ep2_races },
                              { reliability: data.ep3_reliability, cost: data.ep3_cost, applicability: data.ep3_applicability, races: data.ep3_races }
                         ];
                         item.value = data;
                    })
                    .catch(err => {
                         console.error('Error fetching detail:', err);
                         item.value = null;
                    });
            }
        }

        function toggleEdit() {
             if (isEditMode.value) {
                  // If Cancel, Reload to discard changes
                  loadDetail();
             }
             isEditMode.value = !isEditMode.value;
        }

        function openModal() {
             isModalActive.value = true;
        }

        function uploadImage(event) {
             const file = event.target.files[0];
             if (!file) return;

             const formData = new FormData();
             formData.append('file', file);

             fetch('/api/upload', {
                  method: 'POST',
                  body: formData
             })
             .then(r => r.json())
             .then(data => {
                  if (data.url) {
                       item.value.phenomenon_image = data.url; // Save updated absolute/relative url
                       alert('Image uploaded successfully!');
                  } else {
                       alert('Upload error: ' + JSON.stringify(data));
                  }
             })
             .catch(err => alert('Upload exception: ' + err));
        }

        function saveChanges() {
             if (!item.value) return;
             
             // Dynamic payload mapping everything in item
             const payload = { ...item.value };
             delete payload.ep_directions; // Clean calculated nodes
             delete payload.history;      // Clean History to avoid backend parsing errors

             fetch(`/api/cases/${item.value.qr_number}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(payload)
             })
             .then(r => r.json())
             .then(data => {
                  if (data.message) {
                       alert('Updated successfully!');
                       isEditMode.value = false;
                       loadDetail(); // Reload to get updated Audit Logs in Timeline
                  } else {
                       alert('Error: ' + JSON.stringify(data));
                  }
             })
             .catch(err => alert('Error updating case: ' + err));
        }

        return {
            item,
            selectedTab,
            isModalActive,
            isEditMode,
            toggleEdit,
            openModal,
            uploadImage,
            saveChanges
        };
    }
}).mount('#app');
