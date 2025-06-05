FROM nginx

RUN rm /etc/nginx/conf.d/default.conf

RUN touch /etc/ssl/certs/cert.pem /etc/ssl/private/key.key

COPY ./cert.pem /etc/ssl/certs/cert.pem
COPY ./key.key /etc/ssl/private/key.key

COPY ./default.conf /etc/nginx/conf.d/default.conf

RUN mkdir /static
COPY ./static/ /static/


EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
