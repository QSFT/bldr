FROM {docker_from}

ARG NONPRIV_USER_UID
ARG NONPRIV_USER_NAME

# Set the locale
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

ADD files /

ADD hooks/pre-init /hooks/pre-init
RUN /hooks/pre-init

RUN init-docker-image

ADD control /

ADD hooks/pre-install-deps /hooks/pre-install-deps
RUN /hooks/pre-install-deps

RUN install-build-deps

ADD hooks/post-install-deps /hooks/post-install-deps
RUN /hooks/post-install-deps

ADD hooks/pre-build /hooks/pre-build
