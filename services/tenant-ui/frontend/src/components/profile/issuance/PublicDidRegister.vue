<template>
  <div v-if="showDidRegister">
    <Button
      title="Create cheqd DID"
      icon="pi pi-file-export"
      class="p-button-rounded p-button-icon-only p-button-text"
      @click="registerPublicDid()"
    />
  </div>

  <div v-if="showRegistered">
    <i
      v-tooltip="'cheqd DID has been created. See details below.'"
      class="pi pi-check-circle text-green-600"
    ></i>
  </div>
</template>

<script setup lang="ts">
// Vue/Primevue
import { computed } from 'vue';
import Button from 'primevue/button';
import StatusChip from '@/components/common/StatusChip.vue';
import { useToast } from 'vue-toastification';
// State
import { useTenantStore } from '@/store';
import { storeToRefs } from 'pinia';

// Props
const props = defineProps<{
  ledgerInfo: any;
}>();

const toast = useToast();

// State
const tenantStore = useTenantStore();
const { publicDid } =
  storeToRefs(tenantStore);

// Register DID - simplified for cheqd (no transaction handling needed)
const registerPublicDid = async () => {
  try {
    await tenantStore.registerPublicDid();
    toast.success('cheqd DID created successfully');
  } catch (error) {
    toast.error(`Failure while creating DID: ${error}`);
  }
};

// Show the DID registration button when no public DID exists (cheqd doesn't need endorser)
const showDidRegister = computed(
  () => !hasPublicDid.value
);

// Show the DID complete checkmark if it's sucessfull
const hasPublicDid = computed(
  () => !!publicDid.value && !!publicDid.value?.did
);
const showRegistered = computed(
  () => hasPublicDid.value
);
</script>
