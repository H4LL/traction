<template>
  <div class="px-4 py-8 md:px-6 lg:px-8 text-center">
    <div class="center-boxed">
      <div class="img-holder">
        <img src="/img/xanadu/logo.svg" />
        <img
          class="img-holder-smaller"
          src="/img/logo/traction-logo-bc-text.svg"
        />
      </div>
    </div>
    <!-- <div class="mt-3 mb-3 font-bold text-2xl">
      <span class="text-900">{{ $t('dashboard.greeting') }}</span>
    </div> -->
  </div>
</template>

<style>
.center-boxed {
  display: flex;
  align-items: center;
  justify-content: center;
}

.img-holder {
  width: 300px;
  height: 200px;
}

.img-holder-smaller {
  width: 150px;
  height: 50px;
}
</style>
